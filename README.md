# Magic Mirror

A simple, real-time text sharing application that works like magic! Share text instantly between devices on your network.

## Features

- Real-time text synchronization
- IP-based content isolation
- Automatic QR code generation
- Analytics tracking
- Debug information
- No installation required for users

## Development Setup

1. Clone the repository:
```bash
git clone https://github.com/harmonyinfotech/mirror.git
cd mirror
```

2. Create a virtual environment:
```bash
python3 -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
```

3. Install dependencies:
```bash
pip install -r requirements.txt
```

4. Run the development server:
```bash
python app.py
```

## Production Deployment

The application is deployed at `/var/www/mirror` on the production server. Here's how to update it:

1. SSH into the server and navigate to the app directory:
```bash
cd /var/www/mirror
```

2. Activate the virtual environment:
```bash
source venv/bin/activate
```

3. Pull the latest changes:
```bash
git pull
```

4. Install any new dependencies:
```bash
pip install -r requirements.txt
```

5. Restart the service:
```bash
sudo systemctl restart mirror
```

## File Structure

- `app.py`: Main application file
- `templates/`: HTML templates
- `analytics.db`: SQLite database for analytics (auto-created)
- `logs/`: Application logs
- `requirements.txt`: Python dependencies

## Analytics

The application uses SQLite to store analytics data in `analytics.db`. This includes:
- Total page views
- Daily views
- Online device count
- Unique visitors

The database is automatically created when the application starts.

## Security

- Content is isolated by IP address
- No sensitive data is stored
- All data is temporary and in-memory except for analytics

## Troubleshooting

If you encounter issues:

1. Check the logs:
```bash
tail -f /var/www/mirror/logs/app.log
```

2. View debug information at `/debug` endpoint

3. Verify service status:
```bash
sudo systemctl status mirror
```

## License

MIT License - Feel free to use and modify!
