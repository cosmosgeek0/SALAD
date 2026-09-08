#!/usr/bin/perl
use strict;
use warnings;
use JSON::PP;
use HTTP::Tiny;
use Time::HiRes qw(time sleep);
use Time::Local qw(timegm);
use Time::Piece;
use Fcntl qw(:flock O_WRONLY O_NONBLOCK);
use Scalar::Util qw(looks_like_number);

my $SAMPLE_MS = 10_000;
my $HEALTH_MS = 30_000;
my $OFFLINE_GRACE_MS = 120_000;
my $RESTART_GRACE_MS = 120_000;
my $HEALTHY_RESET_MS = 300_000;
my $MAX_RESTARTS = 2;
my $SESSION = '/config/xdg/data/io.getgrass.desktop/store.json';
my $STATE = '/run/grass-recovery.json';

sub now_ms { return int(time() * 1000); }
sub read_file {
    open my $file, '<', $_[0] or return undef;
    local $/;
    return <$file>;
}
sub decoded {
    my $value = $_[0];
    return undef unless defined $value;
    return eval { decode_json($value) } // $value;
}
sub stamp {
    my $value = $_[0] // '';
    return undef unless $value =~ /\A(\d{4})-(\d\d)-(\d\d)T(\d\d):(\d\d):(\d\d)(?:\.(\d+))?Z\z/;
    return eval { timegm($6, $5, $4, $3, $2 - 1, $1) * 1000 + int(('0.' . ($7 // 0)) * 1000) };
}
sub emit {
    my ($ctx, $kind, $value) = @_;
    my $row = {kind => $kind, revision => 2, group_id => $ctx->{group_id},
        instance => $ctx->{instance}, machine => $ctx->{machine}, run => $ctx->{run},
        source_ms => now_ms(), %$value};
    $row->{request_ms} = $ctx->{recovery}{requested_ms} if $kind eq 'grass_event' && $ctx->{recovery}{requested_ms};
    print {$ctx->{output}} ($kind eq 'grass_sample' ? 'GRASS_SAMPLE_V2 ' : 'GRASS_EVENT_V2 '), encode_json($row), "\n";
}
sub save_recovery {
    my ($ctx) = @_;
    open my $file, '>', "$STATE.tmp" or die "Grass recovery state cannot be written\n";
    print {$file} encode_json({container_run => $ctx->{container_run}, %{$ctx->{recovery}}});
    close $file or die "Grass recovery state cannot be closed\n";
    rename "$STATE.tmp", $STATE or die "Grass recovery state cannot be published\n";
}
sub process {
    for my $path (sort glob '/proc/[0-9]*/comm') {
        next unless (read_file($path) // '') eq "grass-desktop\n";
        $path =~ m{/proc/(\d+)/};
        my $pid = 0 + $1;
        my $value = read_file("/proc/$pid/stat") // '';
        my ($state) = $value =~ /\) ([A-Zt]) /;
        next if ($state // '') eq 'Z';
        return ($pid, $state);
    }
    return (undef, undef);
}
sub provider_request {
    my ($ctx, $path, $token) = @_;
    my $reply = $ctx->{http}->get('https://api.grass.io/' . $path, {headers => {Authorization => $token}});
    my $body = eval { decode_json($reply->{content}) };
    return ($reply, ref($body) eq 'HASH' ? $body : {});
}
sub retry_after_ms {
    my ($reply) = @_;
    my $after = $reply->{headers}{'retry-after'};
    return undef unless defined $after;
    return 1000 * $after if $after =~ /\A\d+\z/;
    my $date = eval { Time::Piece->strptime($after, '%a, %d %b %Y %H:%M:%S GMT')->epoch * 1000 };
    my $at = now_ms();
    return defined($date) && $date > $at ? $date - $at : undef;
}
sub observe {
    my ($ctx) = @_;
    my $at = now_ms();
    my ($pid, $process_state) = process();
    my $health = {observed_ms => $at, pid => $pid, process_state => $process_state,
        state => 'unknown', error => undef, device_id => undef, quality => undef};
    if (!$pid) {
        return {%$health, state => 'client_missing', error => 'Grass process is not running'};
    }
    if (($process_state // '') =~ /[Tt]/) {
        return {%$health, state => 'client_stalled', error => 'Grass process is suspended'};
    }
    my $session = eval { decode_json(read_file($SESSION) // '') } // {};
    my $token = decoded($session->{accessToken});
    my $device = decoded($session->{'wynd:device_id'});
    $health->{account_id} = decoded($session->{'wynd:user_id'});
    if (!defined($token) || ref($token) || !$token || !decoded($session->{'wynd:authenticated'})) {
        return {%$health, state => 'login_required', error => 'Grass sign-in is required'};
    }
    if (!defined($device) || ref($device) || !$device) {
        return {%$health, state => 'starting', error => 'Grass is registering this device'};
    }
    $health->{device_id} = $device;
    if (defined($ctx->{last_token}) && $ctx->{last_token} ne $token) {
        delete $ctx->{recovery}{provider_retry_ms};
    }
    $ctx->{last_token} = $token;
    if ($at < ($ctx->{recovery}{provider_retry_ms} // 0)) {
        return {%$health, error => $ctx->{provider_error} // 'Grass status requests are waiting for their retry time',
            retry_after_ms => $ctx->{recovery}{provider_retry_ms} - $at};
    }
    if (!$ctx->{ip_observed_ms} || $at - $ctx->{ip_observed_ms} >= 60_000) {
        my $reply = $ctx->{http}->get('http://ip-api.com/json/?fields=status,query,countryCode');
        my $location = eval { decode_json($reply->{content}) } // {};
        if ($reply->{status} == 200 && ($location->{query} // '') =~ /\A\d{1,3}(?:\.\d{1,3}){3}\z/) {
            $ctx->{ip} = $location->{query};
            $ctx->{country} = ($location->{countryCode} // '') =~ /\A[A-Z]{2}\z/ ? $location->{countryCode} : undef;
            $ctx->{ip_observed_ms} = now_ms();
        } else {
            $ctx->{ip} = undef;
            $ctx->{country} = undef;
            return {%$health, error => 'Current public IP could not be checked'};
        }
    }
    my ($reply, $body) = provider_request($ctx, 'activeDevices', $token);
    $health->{observed_ms} = now_ms();
    $health->{http} = 0 + $reply->{status};
    $health->{http_attempted} = JSON::PP::true;
    if ($reply->{status} == 401 || $reply->{status} == 403) {
        return {%$health, state => 'login_required', error => 'Grass rejected the saved session; sign-in is required'};
    }
    if ($reply->{status} != 200) {
        my $after = retry_after_ms($reply);
        $health->{retry_after_ms} = $after if defined $after;
        return {%$health, error => 'Grass status API returned HTTP ' . $reply->{status}};
    }
    my $rows = ref($body->{result}) eq 'HASH' ? $body->{result}{data} : undef;
    return {%$health, error => 'Grass status response has an unexpected format'}
        unless ref($rows) eq 'ARRAY' && !grep {ref($_) ne 'HASH'} @$rows;
    my ($device_row) = grep {($_->{deviceId} // '') eq $device && ($_->{ipAddress} // '') eq ($ctx->{ip} // '')} @$rows;
    if (!$device_row || !$device_row->{lastConnectedAt}) {
        $health->{state} = 'offline';
        $health->{error} = 'Grass does not list this device and current IP as connected';
    } elsif (!looks_like_number($device_row->{ipScore}) || $device_row->{ipScore} < 0 || $device_row->{ipScore} > 100) {
        $health->{error} = 'Grass did not report a usable network-quality reading';
    } else {
        $health->{quality} = 0 + $device_row->{ipScore};
        $health->{connected_at_ms} = stamp($device_row->{lastConnectedAt});
        $health->{state} = $health->{quality} > 0 ? 'connected' : 'network_rejected';
        $health->{error} = 'Grass reports zero network quality for this IP' if $health->{state} eq 'network_rejected';
    }
    if ((!$ctx->{points_checked_ms} || now_ms() - $ctx->{points_checked_ms} >= 60_000)
        && now_ms() >= ($ctx->{recovery}{points_retry_ms} // 0)) {
        $ctx->{points_checked_ms} = now_ms();
        my $query = encode_json({limit => 1, isLatestOnly => JSON::PP::true});
        $query =~ s/([^A-Za-z0-9_.~-])/sprintf('%%%02X', ord($1))/eg;
        my ($points_reply, $points_body) = provider_request($ctx, 'epochEarnings?input=' . $query, $token);
        my $epoch = eval { $points_body->{result}{data}{data}[0] };
        if ($points_reply->{status} == 200 && ref($epoch) eq 'HASH'
            && looks_like_number($epoch->{proxyPoints}) && $epoch->{proxyPoints} >= 0
            && looks_like_number($epoch->{totalPoints}) && $epoch->{totalPoints} >= 0) {
            $ctx->{provider} = {observed_ms => now_ms(), epoch => $epoch->{epochName}, stage => $epoch->{stage},
                account_id => $epoch->{userId},
                start_date => $epoch->{startDate}, end_date => $epoch->{endDate}, modified_at => $epoch->{modified},
                network_points => 0 + $epoch->{proxyPoints}, total_points => 0 + $epoch->{totalPoints},
                scope => 'account_finalized_epoch', error => undef};
            delete $ctx->{recovery}{points_retry_ms};
        } else {
            my $after = retry_after_ms($points_reply) // 60_000;
            $ctx->{recovery}{points_retry_ms} = now_ms() + ($after > 60_000 ? $after : 60_000);
            $ctx->{provider} //= {};
            $ctx->{provider}{error} = 'Grass points API returned HTTP ' . $points_reply->{status};
            $ctx->{provider}{checked_ms} = now_ms();
        }
    }
    return $health;
}
sub recovery_action {
    my ($health, $saved, $at, $seed_ready) = @_;
    my $state = $health->{state};
    if ($state eq 'connected') {
        delete $saved->{bad_since_ms};
        $saved->{zero_quality_reads} = 0;
        $saved->{healthy_since_ms} //= $at;
        $saved->{attempts} = 0 if $at - $saved->{healthy_since_ms} >= $HEALTHY_RESET_MS;
        return undef;
    }
    delete $saved->{healthy_since_ms};
    if ($state eq 'unknown' || $state eq 'login_required') {
        delete $saved->{bad_since_ms};
        $saved->{zero_quality_reads} = 0;
        return undef;
    }
    $saved->{bad_since_ms} //= $at;
    return undef if $at < ($saved->{next_action_ms} // 0);
    if ($state eq 'network_rejected') {
        $saved->{zero_quality_reads} = ($saved->{zero_quality_reads} // 0) + 1;
        return undef if $saved->{zero_quality_reads} < 2;
        return $seed_ready ? 'reallocate' : 'replacement_requires_seed';
    }
    $saved->{zero_quality_reads} = 0;
    my $grace = $state eq 'client_stalled' ? 0 : $state eq 'client_missing' ? 20_000 : $OFFLINE_GRACE_MS;
    return undef if $at - $saved->{bad_since_ms} < $grace;
    if (($saved->{attempts} // 0) >= $MAX_RESTARTS) {
        return $seed_ready ? 'reallocate' : 'replacement_requires_seed';
    }
    return 'restart_app';
}
sub perform_action {
    my ($ctx, $action) = @_;
    my $saved = $ctx->{recovery};
    my $at = now_ms();
    my $reason = $ctx->{health}{state};
    $saved->{last_action} = $action;
    $saved->{last_reason} = $reason;
    $saved->{requested_ms} = $at;
    $saved->{old_pid} = $ctx->{health}{pid};
    $saved->{next_action_ms} = $at + $RESTART_GRACE_MS;
    delete $saved->{resolved_ms};
    save_recovery($ctx);
    if ($action eq 'replacement_requires_seed') {
        $saved->{error} = 'Machine replacement needs the saved Grass login seed; local recovery remains available';
        emit($ctx, 'grass_event', {event => 'replacement_unavailable', action => $action, reason => $reason});
        return;
    }
    emit($ctx, 'grass_event', {event => 'requested', action => $action, reason => $reason, attempt => ($saved->{attempts} // 0) + 1});
    if ($action eq 'restart_app') {
        $saved->{attempts} = ($saved->{attempts} // 0) + 1;
        kill 'CONT', $saved->{old_pid} if $reason eq 'client_stalled' && $saved->{old_pid};
        if (sysopen(my $pipe, '/tmp/.cinit_cmd', O_WRONLY | O_NONBLOCK)) {
            my $ok = print {$pipe} "restart:app\n";
            close $pipe;
            if ($ok) {
                $saved->{phase} = 'restarting';
                delete $saved->{error};
                emit($ctx, 'grass_event', {event => 'accepted', action => $action, reason => $reason});
            } else {
                $saved->{error} = 'Grass supervisor restart request could not be written';
            }
        } else {
            $saved->{error} = 'Grass supervisor command pipe is unavailable';
        }
    } else {
        $saved->{phase} = 'reallocating';
        for my $attempt (1 .. 3) {
            my $reply = $ctx->{http}->post('http://169.254.169.254/v1/reallocate',
                {headers => {'Metadata' => 'true', 'Content-Type' => 'application/json'},
                 content => encode_json({reason => 'Grass recovery: ' . $reason})});
            emit($ctx, 'grass_event', {event => 'response', action => $action, reason => $reason,
                attempt => $attempt, http => 0 + $reply->{status}});
            if ($reply->{status} == 200 || $reply->{status} == 204) {
                $saved->{accepted_ms} = now_ms();
                save_recovery($ctx);
                emit($ctx, 'grass_event', {event => 'accepted', action => $action, reason => $reason});
                kill 'TERM', 1;
                return;
            }
            sleep 5 if $attempt < 3;
        }
        $saved->{phase} = 'reallocation_failed';
        $saved->{error} = 'Salad did not accept the machine replacement; another attempt is scheduled';
    }
    emit($ctx, 'grass_event', {event => 'failed', action => $action, reason => $reason, error => $saved->{error}}) if $saved->{error};
    save_recovery($ctx);
}
sub sample {
    my ($ctx, $final) = @_;
    my $rx = read_file('/sys/class/net/eth0/statistics/rx_bytes');
    my $tx = read_file('/sys/class/net/eth0/statistics/tx_bytes');
    my $uptime = read_file('/proc/uptime');
    die "Grass network counters unavailable\n" unless defined($rx) && defined($tx) && defined($uptime);
    emit($ctx, 'grass_sample', {seq => $ctx->{seq}++, monotonic_ms => int((split /\s+/, $uptime)[0] * 1000),
        rx => 0 + $rx, tx => 0 + $tx, ip => $ctx->{ip}, country => $ctx->{country},
        health => $ctx->{health}, provider => $ctx->{provider}, recovery => $ctx->{recovery},
        replacement_ready => $ctx->{seed_ready} ? JSON::PP::true : JSON::PP::false,
        final => $final ? JSON::PP::true : JSON::PP::false});
}
sub main {
    umask 0077;
    open my $lock, '>>', '/run/grass-worker.lock' or die "Grass worker lock unavailable\n";
    flock($lock, LOCK_EX | LOCK_NB) or exit 0;
    my $instance = $ENV{SALAD_INSTANCE_ID} // die "Salad instance identity unavailable\n";
    my $machine = $ENV{SALAD_MACHINE_ID} // die "Salad machine identity unavailable\n";
    my $group = $ENV{SALAD_CONTAINER_GROUP_ID} // die "Salad group identity unavailable\n";
    my $stat = read_file('/proc/1/stat') // die "Container identity unavailable\n";
    my @stat = split /\s+/, (split /\) /, $stat, 2)[1];
    my $container_run = "$instance:$machine:$stat[19]";
    my $saved = eval { decode_json(read_file($STATE) // '') } // {};
    $saved = {} unless ($saved->{container_run} // '') eq $container_run;
    delete $saved->{container_run};
    open my $output, '>', '/proc/1/fd/1' or die "Container log stream unavailable\n";
    $output->autoflush(1);
    my $ctx = {instance => $instance, machine => $machine, group_id => $group,
        container_run => $container_run, run => $container_run . ':' . now_ms(), output => $output,
        seq => 0, recovery => $saved, health => {state => 'starting', observed_ms => now_ms()},
        seed_ready => -f '/run/grass-seed-ready', http => HTTP::Tiny->new(timeout => 8, verify_SSL => 1)};
    my $quit = 0;
    $SIG{TERM} = sub { $quit = 1 };
    $SIG{INT} = sub { $quit = 1 };
    my ($next_health, $next_sample, $failures) = (0, 0, 0);
    emit($ctx, 'grass_event', {event => 'worker_started', replacement_ready => $ctx->{seed_ready} ? JSON::PP::true : JSON::PP::false});
    while (!$quit) {
        my $at = now_ms();
        if ($at >= $next_sample) {
            my ($pid, $state) = process();
            $next_health = 0 if !$pid || ($state // '') =~ /[Tt]/;
        }
        if ($at >= $next_health) {
            $ctx->{health} = observe($ctx);
            my $health = $ctx->{health};
            if ($health->{http_attempted}) {
                $failures = $health->{state} eq 'unknown' ? $failures + 1 : 0;
                if ($failures) {
                    my $pause = $health->{retry_after_ms} // ($HEALTH_MS * 2 ** ($failures > 5 ? 5 : $failures));
                    $pause = $HEALTH_MS if $pause < $HEALTH_MS;
                    $saved->{provider_retry_ms} = now_ms() + $pause;
                    $ctx->{provider_error} = $health->{error};
                } else {
                    delete $saved->{provider_retry_ms};
                    delete $ctx->{provider_error};
                }
            }
            $next_health = now_ms() + $HEALTH_MS;
            $health->{next_check_ms} = ($saved->{provider_retry_ms} // 0) > $next_health ? $saved->{provider_retry_ms} : $next_health;
            if (($saved->{phase} // '') =~ /\A(?:restarting|restart_unconfirmed)\z/ && $health->{state} eq 'connected'
                && ($health->{pid} // 0) != ($saved->{old_pid} // 0)) {
                $saved->{phase} = 'recovered';
                $saved->{resolved_ms} = now_ms();
                delete $saved->{error};
                emit($ctx, 'grass_event', {event => 'recovered', action => 'restart_app', reason => $saved->{last_reason}, requested_ms => $saved->{requested_ms}});
            } elsif (($saved->{phase} // '') eq 'restarting' && now_ms() >= ($saved->{next_action_ms} // 0)) {
                $saved->{phase} = 'restart_unconfirmed';
                $saved->{error} = 'The requested app restart has no confirmed replacement process and connection yet';
                emit($ctx, 'grass_event', {event => 'unconfirmed', action => 'restart_app', requested_ms => $saved->{requested_ms}});
            }
            my $action = recovery_action($health, $saved, now_ms(), $ctx->{seed_ready});
            perform_action($ctx, $action) if defined $action;
            save_recovery($ctx);
        }
        if (now_ms() >= $next_sample) {
            sample($ctx, 0);
            $next_sample = (int(now_ms() / $SAMPLE_MS) + 1) * $SAMPLE_MS;
        }
        sleep 1;
    }
    $ctx->{health} = {state => 'stopping', observed_ms => now_ms()};
    sample($ctx, 1);
    emit($ctx, 'grass_event', {event => 'worker_stopped'});
}

main() unless caller;
