# Business Idea Hunter

Automated startup problem discovery from Reddit and Hacker News.

## Setup

```bash
# Clone / copy project
cd business_idea_hunter

# Create virtual environment
python3.11 -m venv venv
source venv/bin/activate

# Install dependencies
pip install -r requirements.txt

# Configure environment
cp .env.example .env
# Edit .env with your API keys
nano .env

# Initialize database and run pipeline
python -m pipeline.run_pipeline

# Start Streamlit
streamlit run app/app.py --server.port 8501 --server.headless true
```

## Architecture

```
Sources (Reddit, AskHN)
    ↓
Pipeline (fetch → filter → extract → embed → cluster → score)
    ↓
SQLite Database
    ↓
Streamlit Dashboard
```

## Adding New Sources

1. Create `sources/my_source.py`
2. Inherit from `BaseSource`
3. Implement `fetch()` returning `list[RawPost]`
4. Register in `pipeline/run_pipeline.py` → `get_enabled_sources()`

## Scoring

| Component    | Weight | Source                          |
|-------------|--------|---------------------------------|
| Engagement  | 0–20   | log(upvotes) + log(comments)    |
| Pain        | 0–20   | LLM pain_score × 2             |
| Monetization| 0–20   | LLM monetization_score × 2     |
| Frequency   | 0–20   | log(cluster_size) × 6          |
| Momentum    | 0–20   | log(7-day cluster growth) × 8  |

Final score: sum of all components, capped at 100.

---

## systemd Service: Streamlit App

`/etc/systemd/system/ideahunter-web.service`

```ini
[Unit]
Description=Business Idea Hunter - Streamlit App
After=network.target

[Service]
Type=simple
User=ubuntu
Group=ubuntu
WorkingDirectory=/home/ubuntu/business_idea_hunter
Environment="PATH=/home/ubuntu/business_idea_hunter/venv/bin:/usr/bin"
ExecStart=/home/ubuntu/business_idea_hunter/venv/bin/streamlit run app/app.py \
    --server.port 8501 \
    --server.headless true \
    --server.address 127.0.0.1
Restart=always
RestartSec=5

[Install]
WantedBy=multi-user.target
```

## systemd Service + Timer: Pipeline

`/etc/systemd/system/ideahunter-pipeline.service`

```ini
[Unit]
Description=Business Idea Hunter - Pipeline Run
After=network.target

[Service]
Type=oneshot
User=ubuntu
Group=ubuntu
WorkingDirectory=/home/ubuntu/business_idea_hunter
Environment="PATH=/home/ubuntu/business_idea_hunter/venv/bin:/usr/bin"
ExecStart=/home/ubuntu/business_idea_hunter/venv/bin/python -m pipeline.run_pipeline
TimeoutStartSec=1800
```

`/etc/systemd/system/ideahunter-pipeline.timer`

```ini
[Unit]
Description=Run Business Idea Hunter pipeline at 08:00 and 20:00

[Timer]
OnCalendar=*-*-* 08:00:00
OnCalendar=*-*-* 20:00:00
Persistent=true

[Install]
WantedBy=timers.target
```

### Enable services

```bash
sudo systemctl daemon-reload
sudo systemctl enable --now ideahunter-web.service
sudo systemctl enable --now ideahunter-pipeline.timer
```

### Check status

```bash
sudo systemctl status ideahunter-web
sudo systemctl status ideahunter-pipeline.timer
sudo journalctl -u ideahunter-pipeline -f
```

---

## Caddy Reverse Proxy

`/etc/caddy/Caddyfile`

```
ideas.yourdomain.com {
    reverse_proxy 127.0.0.1:8501

    header {
        X-Content-Type-Options "nosniff"
        X-Frame-Options "DENY"
        Referrer-Policy "strict-origin-when-cross-origin"
    }

    encode gzip

    @websockets {
        header Connection *Upgrade*
        header Upgrade websocket
    }
    reverse_proxy @websockets 127.0.0.1:8501
}
```

```bash
sudo systemctl reload caddy
```
