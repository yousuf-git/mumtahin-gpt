# 🧠 Setting up MumtahinGPT as a Systemd Service (Ubuntu EC2)

This guide explains how to run MumtahinGPT as a background service using **systemd**, ensuring it auto-starts on reboot and uses your virtual environment.

**Note:** This guide is configured for **v2_rag** (RAG-based version) by default. 
For **v1_basic** deployment, see comments marked with `# For v1_basic`.

---

## 📂 Project Structure

```
/home/ubuntu/mumtahin-gpt/
│
├── v1_basic/              # Basic version without RAG
│   ├── app.py
│   ├── examiner_logic.py
│   ├── pdf_handler.py
│   └── venv/
│
├── v2_rag/                # RAG-based version (MAIN)
│   ├── app.py
│   ├── examiner_logic.py
│   ├── pdf_handler.py
│   └── venv/
│
├── requirements.txt
└── other files...
```

---

## ⚙️ 1. Create and Activate Virtual Environment

```bash
# ========================================
# For v2_rag (RAG-based version - MAIN)
# ========================================
cd /home/ubuntu/mumtahin-gpt/v2_rag
python3.11 -m venv venv
source venv/bin/activate
cd ..
pip install -r requirements.txt

# ========================================
# For v1_basic (Basic version)
# ========================================
# cd /home/ubuntu/mumtahin-gpt/v1_basic
# python3.11 -m venv venv
# source venv/bin/activate
# cd ..
# pip install -r requirements.txt
```

✅ Verify correct Python version:
```bash
python --version
# should show Python 3.11.x
```

Deactivate after installing:
```bash
deactivate
```

---

## 🧾 2. Create a Systemd Service File

```bash
sudo nano /etc/systemd/system/mumtahingpt.service
```

Paste the following configuration (update paths as needed):

```ini
# ========================================
# MAIN VERSION: v2_rag (RAG-based)
# ========================================
[Unit]
Description=MumtahinGPT v2 (RAG-based)
After=network.target

[Service]
User=ubuntu
WorkingDirectory=/home/ubuntu/mumtahin-gpt/v2_rag
ExecStart=/home/ubuntu/mumtahin-gpt/v2_rag/venv/bin/python3.11 /home/ubuntu/mumtahin-gpt/v2_rag/app.py
Restart=always
Environment=PYTHONUNBUFFERED=1
StandardOutput=append:/var/log/mumtahingpt.log
StandardError=append:/var/log/mumtahingpt.log

[Install]
WantedBy=multi-user.target

# ========================================
# ALTERNATIVE: v1_basic (Basic version)
# ========================================
# [Unit]
# Description=MumtahinGPT v1 (Basic)
# After=network.target
# 
# [Service]
# User=ubuntu
# WorkingDirectory=/home/ubuntu/mumtahin-gpt/v1_basic
# ExecStart=/home/ubuntu/mumtahin-gpt/v1_basic/venv/bin/python3.11 /home/ubuntu/mumtahin-gpt/v1_basic/app.py
# Restart=always
# Environment=PYTHONUNBUFFERED=1
# StandardOutput=append:/var/log/mumtahingpt.log
# StandardError=append:/var/log/mumtahingpt.log
# 
# [Install]
# WantedBy=multi-user.target
```

> 💡 `StandardOutput` & `StandardError` will log everything to `/var/log/mumtahingpt.log`.

---

## 🪄 3. Set Log File Permissions

```bash
sudo touch /var/log/mumtahingpt.log
sudo chown ubuntu:ubuntu /var/log/mumtahingpt.log
```

---

## 🔁 4. Enable and Start the Service

```bash
sudo systemctl daemon-reload
sudo systemctl enable mumtahingpt.service
sudo systemctl start mumtahingpt.service
```

---

## 🧩 5. Verify Service Status

```bash
sudo systemctl status mumtahingpt.service
```

Expected output:
```
● mumtahingpt.service - MumtahinGPT v2 (RAG-based)
     Loaded: loaded (/etc/systemd/system/mumtahingpt.service; enabled)
     Active: active (running)
   Main PID: 12345 (python3.11)
      Tasks: 3
```

---

## 📜 6. Check Logs

Using systemd logs:
```bash
journalctl -u mumtahingpt.service -f
```

Or directly from your log file:
```bash
tail -f /var/log/mumtahingpt.log
```

---

## 🔄 7. Managing the Service

| Action | Command |
|--------|----------|
| **Start service** | `sudo systemctl start mumtahingpt.service` |
| **Stop service** | `sudo systemctl stop mumtahingpt.service` |
| **Restart service** | `sudo systemctl restart mumtahingpt.service` |
| **View logs** | `journalctl -u mumtahingpt.service -n 20` |
| **Enable auto-start** | `sudo systemctl enable mumtahingpt.service` |
| **Disable auto-start** | `sudo systemctl disable mumtahingpt.service` |

---

## 🚀 8. Test Auto-Start on Reboot

Reboot your EC2 instance:
```bash
sudo reboot
```

After it restarts, check:
```bash
sudo systemctl status mumtahingpt.service
```

It should show:
```
Active: active (running)
```

---

## 🧰 9. Common Troubleshooting

| Issue | Cause | Fix |
|--------|-------|-----|
| `ModuleNotFoundError` | System using global Python | Use venv's `python3.11` in `ExecStart` |
| `Permission denied` | Wrong file ownership | `sudo chown -R ubuntu:ubuntu /home/ubuntu/mumtahin-gpt` |
| No `.env` variables | Not loaded by systemd | Add `EnvironmentFile=/home/ubuntu/mumtahin-gpt/v2_rag/.env` (or v1_basic) |
| Service keeps restarting | Crash on startup | Temporarily set `Restart=no` to debug |
| No logs visible | Not configured | Add `StandardOutput` and `StandardError` lines |

---

## ✅ Final Notes
- Uses **Python 3.11** explicitly.
- Runs in **virtual environment** (v2_rag or v1_basic).
- Automatically restarts on failure.
- Starts on **boot**.
- Logs stored in `/var/log/mumtahingpt.log`.
- **v2_rag** includes RAG support with ChromaDB (recommended).
- **v1_basic** is simpler without RAG dependencies.

---

### Example Verification Command
To confirm it's running from the correct interpreter:
```bash
# For v2_rag
echo 'import sys; print(sys.executable)' | sudo tee /home/ubuntu/mumtahin-gpt/v2_rag/app.py
sudo systemctl restart mumtahingpt.service
tail -n 5 /var/log/mumtahingpt.log

# For v1_basic
# echo 'import sys; print(sys.executable)' | sudo tee /home/ubuntu/mumtahin-gpt/v1_basic/app.py
```
Output should include:
```
# For v2_rag:
/home/ubuntu/mumtahin-gpt/v2_rag/venv/bin/python3.11

# For v1_basic:
# /home/ubuntu/mumtahin-gpt/v1_basic/venv/bin/python3.11
```

---

🟢 **You're done!** MumtahinGPT now runs as a reliable background service on Ubuntu EC2 using the virtual environment.

**Project:** MumtahinGPT (github.com/yousuf-git/mumtahin-gpt)  
**Last Updated:** December 9, 2025