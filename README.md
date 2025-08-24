# Credit Card Optimizer

This application helps users find the optimal credit card spending strategy to maximize their cashback rewards.

## How to Run

### 1. Install Dependencies

**Backend (Python):**

First, make sure you have Python 3.10 or higher installed.

```bash
# Create a virtual environment
python3 -m venv .venv

# Activate the virtual environment
source .venv/bin/activate

# Install the required packages
pip install -r requirements.txt
```

**Frontend (Node.js):**

First, make sure you have Node.js and npm installed.

```bash
# Navigate to the frontend directory
cd frontend

# Install the required packages
npm install
```

### 2. Run the Application

You will need to run two separate processes in two different terminals.

**Backend Server:**

In one terminal, run the FastAPI server from the root directory of the project:

```bash
# Make sure your virtual environment is activated
source .venv/bin/activate

# Run the backend server
uvicorn api:app --host 0.0.0.0 --port 8000
```

**Frontend Server:**

In another terminal, run the React development server from the `frontend` directory:

```bash
# Navigate to the frontend directory
cd frontend

# Run the frontend server
npm run dev
```

### 3. Access the Application

Once both servers are running, open your web browser and navigate to the address provided by the Vite dev server (usually `http://localhost:5173`). You should see the Credit Card Optimizer application.
