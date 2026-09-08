# Country availability

`check_countries.py` calls Salad's official read-only CPU availability estimator for each country. It does not create, edit, restart or reallocate containers. The defaults match the inspected PacketStream settings: 1 vCPU, 1024 MB RAM, no GPU, no extra storage requirement, Lowest priority.

Run from the repository root:

```sh
python3 availability/check_countries.py
```

For a quick subset or another CPU/RAM size:

```sh
python3 availability/check_countries.py --countries us ca gb de fr in jp au
python3 availability/check_countries.py --cpu 4 --memory 8192
```

The script reuses the existing authorized Mac credential helper. On another host, supply `SALAD_API_KEY` securely in the process environment. Credentials are never written to the report or printed. Python 3's standard library is sufficient; Node, when present, supplies readable country names through its built-in ICU data.

Each run saves a timestamped Markdown table and JSON response data in this folder. Four concurrent requests are used by default, with bounded retries for transient errors and rate limits. Missing/failed results remain unknown. Country options were captured from all 249 entries in the Salad Portal on September 7, 2026.

Availability is an estimate matching the specified resource filters. It is not a reservation, a count of unique public IPs, or evidence of bandwidth-buyer demand. The public definition of `on_call_cpu` is incomplete, so the report preserves that field without interpreting it as deployable replicas. Countries are sampled at slightly different times; their sum can differ from the global count.

Sources: [CPU availability API](https://docs.salad.com/reference/saladcloud-api/organizations/get-cpu-availability), [availability interpretation](https://docs.salad.com/container-engine/explanation/infrastructure-platform/availability).
