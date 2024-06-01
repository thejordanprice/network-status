# Network Status

Network Status is a simple web application that allows users to monitor the online/offline status of IP addresses and their corresponding hostnames. It provides a user-friendly interface for managing IP entries, including adding, editing, and deleting them.

## Features

- Add new IP entries with hostnames
- View a list of IP entries with their corresponding status (online/offline) and response time
- Edit existing IP entries
- Delete IP entries
- Sort IP entries by drag and drop

## Technologies Used

- Flask: Python web framework for building the backend server
- SQLite: Lightweight relational database for storing IP entries and UI settings
- Bootstrap: Frontend framework for styling and layout
- JavaScript: For client-side interaction and dynamic updating
- Sortable.js: JavaScript library for drag-and-drop sorting functionality

## Setup

1. Clone the repository:

```git clone https://github.com/thejordanprice/network-status.git```

2. Install dependencies:

```pip install -r requirements.txt```

3. Run the Flask application:

```python app.py```

4. Access the application in your web browser:

```http://localhost:8000```

## Usage

- Navigate to the application URL in your web browser.
- Use the interface to add, edit, or delete IP entries.
- Monitor the online/offline status and response time of each IP entry.

## Contributing

Contributions are welcome! If you'd like to contribute to this project, please follow these steps:

1. Fork the repository
2. Create a new branch (`git checkout -b feature/new-feature`)
3. Make your changes
4. Commit your changes (`git commit -am 'Add new feature'`)
5. Push to the branch (`git push origin feature/new-feature`)
6. Create a new Pull Request

## License

This project is licensed under the MIT License. See the [LICENSE](LICENSE) file for details.
