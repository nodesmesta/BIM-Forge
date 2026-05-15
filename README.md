# Building Generator

This project is an AI-powered multi-agent building specification to 3D render generator. It uses a FastAPI backend for the agentic workflow and a Next.js frontend for the user interface.

## Prerequisites

Before you begin, ensure you have the following installed:
- [Node.js](https://nodejs.org/) (v18 or later)
- [Python](https://www.python.org/) (v3.10 or later)
- [Make](https://www.gnu.org/software/make/)
- For Debian-based systems (like Ubuntu), you will also need the following development libraries for building Python dependencies:
  ```bash
  sudo apt-get update && sudo apt-get install -y libldap2-dev libsasl2-dev
  ```

## Getting Started

1.  **Clone the repository:**
    ```bash
    git clone <your-repo-url>
    cd Arsitektur
    ```

2.  **Run the setup script:**
    This will install all backend (Python) and frontend (Node.js) dependencies.
    ```bash
    make setup
    ```

3.  **Run the development servers:**
    This command starts both the backend and frontend servers concurrently. Logs will be automatically created in the `service/log` directory.
    ```bash
    make dev
    ```
    - Backend will be available at `http://localhost:8000`
    - Frontend will be available at `http://localhost:3000`


## Available Makefile Commands

- `make dev`: Starts both frontend and backend development servers with logging. This is the recommended command for development.
- `make setup`: Installs all dependencies for both frontend and backend.
- `make stop`: Stops all running development processes.
- `make clean`: Stops all processes and removes all temporary files, logs, and caches (`venv`, `node_modules`, `.next`, `service/log`, etc.).
- `make status`: Shows the status of running development processes.
- `make help`: Displays a list of all available commands.

