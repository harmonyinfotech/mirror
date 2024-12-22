# mirror.is

Share text instantly with devices on your network. No signup, no installation - just open and share.

## Features

- Instant text sharing between devices on the same network
- No account required
- Real-time synchronization
- Clean, modern interface
- Mobile-friendly design
- Temporary storage (content expires after 24 hours)

## Quick Start

1. Clone the repository:
```bash
git clone https://github.com/yourusername/mirror-is.git
cd mirror-is
```

2. Install dependencies:
```bash
pip install -r requirements.txt
```

3. Run the application:
```bash
python app.py
```

4. Open in your browser:
   - Local: `http://localhost:5000`
   - Other devices: `http://your-ip:5000`

## Production Deployment

### Using Gunicorn and Nginx

1. Install Gunicorn:
```bash
pip install gunicorn
```

2. Create a systemd service file `/etc/systemd/system/mirror-is.service`:
```ini
[Unit]
Description=mirror.is text sharing service
After=network.target

[Service]
User=your_user
WorkingDirectory=/path/to/mirror-is
Environment="PATH=/path/to/venv/bin"
ExecStart=/path/to/venv/bin/gunicorn -w 4 -b 127.0.0.1:8000 app:app

[Install]
WantedBy=multi-user.target
```

3. Configure Nginx:
```nginx
server {
    listen 80;
    server_name mirror.is;

    location / {
        proxy_pass http://127.0.0.1:8000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
    }
}
```

4. Start the service:
```bash
sudo systemctl start mirror-is
sudo systemctl enable mirror-is
```

## Security

- Content is shared with anyone on the same network
- No encryption in transit (use HTTPS in production)
- Content expires after 24 hours
- Do not share sensitive information

## Contributing

1. Fork the repository
2. Create your feature branch (`git checkout -b feature/amazing-feature`)
3. Commit your changes (`git commit -m 'Add some amazing feature'`)
4. Push to the branch (`git push origin feature/amazing-feature`)
5. Open a Pull Request

## License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## Acknowledgments

- Inspired by [ssavr.com](https://ssavr.com)
- Built with Flask and modern web technologies
