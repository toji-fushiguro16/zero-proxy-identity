
# Zero-Trust Identity Proxy for Cloud Microservices

A cloud security academic prototype demonstrating identity verification,
JWT authentication, role-based access control, and access audit logging.

## Features
- User registration and login
- Password hashing
- JWT-based authentication
- Admin and user roles
- Protected User and Order services
- Admin-only audit logs
- SQLite database
- Responsive web dashboard

## Technology Stack
- Frontend: HTML, CSS, JavaScript
- Backend: Python, Flask
- Authentication: JWT
- Database: SQLite

## Demo accounts
- Admin username: admin
- Admin password: admin123

New registrations receive the standard user role.

## Run locally

1. Open the backend folder in the terminal.
2. Create and activate a Python virtual environment.
3. Install dependencies:

   pip install -r requirements.txt

4. Run the backend:

   python app.py

5. Open frontend/index.html in a browser, preferably using VS Code Live Server.

The local API runs at http://127.0.0.1:5000.

## Security note
This is an academic demonstration, not a production-ready identity
gateway. Change the default admin credentials and JWT secret before
deployment. Use HTTPS, persistent managed storage, rate limiting,
and additional security controls for real-world deployment.
