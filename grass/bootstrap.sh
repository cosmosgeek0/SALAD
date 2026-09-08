#!/bin/sh
set -eu
export LC_ALL=C
export GRASS_BOOT_STAGE=install_tls
boot_failure() {
    GRASS_BOOT_EXIT="$1" /usr/bin/perl -MJSON::PP -MTime::HiRes=time -e '
        print "GRASS_EVENT_V2 ", encode_json({kind=>"grass_event", revision=>2,
            group_id=>$ENV{SALAD_CONTAINER_GROUP_ID}, instance=>$ENV{SALAD_INSTANCE_ID}, machine=>$ENV{SALAD_MACHINE_ID},
            run=>"$ENV{SALAD_INSTANCE_ID}:$ENV{SALAD_MACHINE_ID}:bootstrap", source_ms=>int(time()*1000),
            event=>"bootstrap_failed", reason=>$ENV{GRASS_BOOT_STAGE}, exit_code=>0+$ENV{GRASS_BOOT_EXIT}}), "\n";
    ' > /proc/1/fd/1
}
trap 'code=$?; if [ "$code" -ne 0 ]; then boot_failure "$code"; fi' EXIT

if ! /usr/bin/perl -MHTTP::Tiny -e 'my ($ok) = HTTP::Tiny->can_ssl; exit($ok ? 0 : 1)'; then
    getent group messagebus >/dev/null || groupadd --system messagebus
    DEBIAN_FRONTEND=noninteractive apt-get update -qq
    DEBIAN_FRONTEND=noninteractive apt-get install -y --no-install-recommends libio-socket-ssl-perl
fi

export GRASS_BOOT_STAGE=restore_login
state_dir=/config/xdg/data/io.getgrass.desktop
mkdir -p "$state_dir"
chown app:app /config/xdg /config/xdg/data "$state_dir"
chmod 700 "$state_dir"
if [ -n "${GRASS_STATE_B64:-}" ]; then
    if [ ! -f "$state_dir/store.json" ]; then
        /usr/bin/perl -MJSON::PP -MMIME::Base64 -e '
            my $raw = decode_base64($ENV{GRASS_STATE_B64});
            my $state = eval { decode_json($raw) };
            die "Grass login seed is invalid\n" unless ref($state) eq "HASH" && $state->{accessToken};
            delete @{$state}{grep { /^wynd:device_/ || $_ eq "wynd:browser_id" || $_ eq "wynd:status" } keys %$state};
            open my $file, ">", "/config/xdg/data/io.getgrass.desktop/store.json" or die "Grass login seed cannot be restored\n";
            print {$file} encode_json($state);
            close $file or die "Grass login seed cannot be saved\n";
        '
        chmod 600 "$state_dir/store.json"
        chown app:app "$state_dir/store.json"
    fi
    touch /run/grass-seed-ready
fi

export GRASS_BOOT_STAGE=install_supervisor
service_dir=/etc/services.d/grass-worker
mkdir -p "$service_dir"
printf '#!/bin/sh\nexport LC_ALL=C\nexec /usr/bin/perl /opt/grass/worker.pl\n' > "$service_dir/run"
chmod 755 "$service_dir/run"
printf '0\n' > "$service_dir/uid"
printf '0\n' > "$service_dir/gid"
printf '1\n' > "$service_dir/respawn"
printf '0\n' > "$service_dir/shutdown_on_terminate"
touch "$service_dir/app.dep" /etc/services.d/default/grass-worker.dep
rm -f /etc/cron.d/grass-sample /usr/local/bin/grass-sample.pl
printf 'GRASS_BOOTSTRAP_READY\n'
