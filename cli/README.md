# Lost & Found CLI Tool

A command-line interface for interacting with the Lost & Found backend API.

## Installation

### From the project root:

```bash
# Install CLI dependencies
pip install click httpx rich

# Install CLI as a package (recommended)
pip install -e .
```

### Or install dependencies directly:

```bash
pip install -r cli/requirements.txt
```

## Usage

After installation, you can use either `lf` or `lostfound` command:

```bash
# Show help
lf --help

# Show version
lf --version
```

## Quick Start

### 1. Configure API URL (if not using default localhost:8000)

```bash
lf config set-url http://your-api-server.com
lf config test  # Test connection
```

### 2. Register and Login

```bash
# Register a new account
lf auth register --email user@example.com --password yourpassword --name "John Doe"

# Login
lf auth login --email user@example.com --password yourpassword

# Check status
lf status
```

### 3. Create a Lost/Found Item

```bash
# Create a lost item
lf items create \
  --type phone \
  --lost \
  --title "Black iPhone 14 Pro" \
  --description "Lost my phone with a black case" \
  --lat 40.7128 \
  --lng -74.0060 \
  --location "Central Park, NYC" \
  --date "2024-01-15T14:30:00"

# Create a found item
lf items create \
  --type wallet \
  --found \
  --title "Brown leather wallet" \
  --lat 40.7589 \
  --lng -73.9851 \
  --date "2024-01-16T09:00:00"
```

### 4. Upload Images

```bash
# Upload an image to an item
lf items upload-image <item-id> /path/to/photo.jpg

# List images for an item
lf items list-images <item-id>
```

### 5. Find Matches

```bash
# Find potential matches for your item
lf matches find <item-id>

# With custom parameters
lf matches find <item-id> --radius 100 --days 60 --min-score 0.5

# List all your matches
lf matches list

# View match details
lf matches get <match-id>
```

### 6. Confirm/Reject Matches

```bash
# Confirm a match
lf matches confirm <match-id>

# Reject a match
lf matches reject <match-id> --reason "Not my item"
```

### 7. Notifications

```bash
# List notifications
lf notifications list

# Show only unread
lf notifications list --unread

# Mark as read
lf notifications read <notification-id>

# Mark all as read
lf notifications read-all
```

## Command Reference

### Authentication (`lf auth`)

| Command | Description |
|---------|-------------|
| `register` | Register a new user account |
| `login` | Login to your account |
| `logout` | Logout and clear credentials |
| `status` | Check authentication status |
| `profile` | View your user profile |
| `update-profile` | Update profile information |
| `delete-account` | Delete your account permanently |

### Items (`lf items`)

| Command | Description |
|---------|-------------|
| `create` | Create a new lost/found item |
| `list` | List your items |
| `get` | Get item details |
| `update` | Update an item |
| `delete` | Delete an item |
| `upload-image` | Upload an image to an item |
| `list-images` | List images for an item |
| `delete-image` | Delete an image |

### Matches (`lf matches`)

| Command | Description |
|---------|-------------|
| `find` | Find potential matches for an item |
| `list` | List all your matches |
| `get` | Get match details |
| `confirm` | Confirm a match |
| `reject` | Reject a match |

### Notifications (`lf notifications`)

| Command | Description |
|---------|-------------|
| `list` | List notifications |
| `get` | View a notification |
| `read` | Mark notification(s) as read |
| `read-all` | Mark all as read |
| `delete` | Delete a notification |

### Configuration (`lf config`)

| Command | Description |
|---------|-------------|
| `show` | Show current configuration |
| `set-url` | Set the backend API URL |
| `set-timeout` | Set request timeout |
| `reset` | Reset to defaults |
| `test` | Test API connection |

### Shortcuts

| Command | Equivalent |
|---------|------------|
| `lf login` | `lf auth login` |
| `lf logout` | `lf auth logout` |
| `lf status` | `lf auth status` |
| `lf whoami` | `lf auth profile` |

## Configuration

Configuration is stored in `~/.lostfound/`:

- `config.json` - CLI settings (API URL, timeout)
- `token.json` - Authentication token (auto-managed)

### Default Settings

- **API URL**: `http://localhost:8000`
- **API Prefix**: `/api/v1`
- **Timeout**: 30 seconds

## Item Types

Valid item types for the `--type` option:

- `phone`, `wallet`, `keys`, `bag`, `laptop`, `tablet`
- `watch`, `jewelry`, `glasses`, `headphones`, `camera`
- `documents`, `pet`, `clothing`, `electronics`, `other`

## Examples

### Complete Workflow

```bash
# 1. Setup
lf config set-url http://localhost:8000
lf auth register -e john@example.com -p mypassword123 -n "John Doe"
lf auth login -e john@example.com -p mypassword123

# 2. Report a lost phone
lf items create \
  --type phone \
  --lost \
  --title "Samsung Galaxy S23" \
  --description "Black phone with cracked screen protector" \
  --lat 37.7749 \
  --lng -122.4194 \
  --location "San Francisco, CA" \
  --date "2024-01-20T18:00:00"

# 3. Upload photos
lf items upload-image abc123 front.jpg
lf items upload-image abc123 back.jpg

# 4. Search for matches
lf matches find abc123 --radius 50 --days 30

# 5. Confirm a match
lf matches confirm xyz789

# 6. Check notifications
lf notifications list --unread
```

### Scripting

The CLI can be used in scripts:

```bash
#!/bin/bash

# Login and save status
lf login -e $EMAIL -p $PASSWORD

# Create item and capture ID
ITEM_ID=$(lf items create --type phone --lost --title "Test" \
  --lat 0 --lng 0 --date "2024-01-01T00:00:00" 2>&1 | grep "ID:" | awk '{print $2}')

# Upload images
for img in *.jpg; do
  lf items upload-image $ITEM_ID "$img"
done

# Find matches
lf matches find $ITEM_ID
```

## Troubleshooting

### "Not logged in" error

```bash
lf auth login -e your@email.com -p yourpassword
```

### Connection refused

Make sure the backend server is running:

```bash
# Check connection
lf config test

# Update URL if needed
lf config set-url http://correct-url:port
```

### Token expired

Simply login again:

```bash
lf auth login -e your@email.com -p yourpassword
```

## Development

### Running without installation

```bash
cd lost&found
python -m cli.main --help
```

### Running tests

```bash
pytest cli/tests/
```
