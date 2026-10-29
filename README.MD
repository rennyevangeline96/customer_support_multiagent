# Customer Support Multi-Agent Router

A Streamlit-based customer support app built with **AutoGen** and **OpenAI**. It routes each customer question to the most relevant specialist agent instead of asking every agent to respond.

## Features

- **Marketing Support** — sales, campaigns, leads, and promotion.
- **IT Support** — technical issues, errors, login problems, and troubleshooting.
- **Finance Support** — invoices, payments, refunds, and billing.
- **HR Support** — leave, attendance, policies, and employee-related questions.
- **Automatic routing** — a selector agent chooses the best department.
- **Bounded workflow** — at most two model calls per question: one routing call and one specialist call.
- **Streamlit chat interface** — ask questions and review answers in the current session.
- **Routing details** — view the selected department and the reason for routing.

## How It Works

1. The user submits a question in the Streamlit interface.
2. The selector agent classifies the question and returns a department and reason.
3. The app calls only the selected specialist agent.
4. The specialist generates a response.
5. The app displays the answer and routing details.

The workflow is intentionally sequential. It does **not** use `RoundRobinGroupChat`, because only one specialist should answer each question. The two-call maximum is enforced by application flow: one selector call plus one specialist call. This prevents an open-ended multi-agent loop.

## Project Structure

```text
customer_support_multiagent/
├── app.py
├── requirements.txt
├── .env
├── .env.example       # Optional template to commit
├── .gitignore
└── README.md
```

## Requirements

- Python 3.10 or a compatible version supported by your installed AutoGen packages
- An OpenAI API key
- Internet access for API requests

## Setup

### 1. Open the project directory

```powershell
cd customer_support_multiagent
```

### 2. Create a virtual environment

```powershell
python -m venv venv
```

### 3. Activate the virtual environment

For **Windows PowerShell**:

```powershell
.\venv\Scripts\Activate.ps1
```

For **Windows Command Prompt (CMD)**:

```cmd
venv\Scripts\activate.bat
```

If PowerShell blocks script execution, allow scripts for the current terminal session:

```powershell
Set-ExecutionPolicy -Scope Process -ExecutionPolicy Bypass
```

Then activate the environment again.

### 4. Install dependencies

```powershell
python -m pip install --upgrade pip
pip install -r requirements.txt
```

### 5. Configure environment variables

Create a file named `.env` in the project root:

```env
OPENAI_API_KEY=your_actual_openai_api_key
OPENAI_MODEL=gpt-4o-mini
```

Replace the placeholder with your own API key. **Never commit `.env` or share your API key.**

Your `requirements.txt` should contain:

```text
autogen-agentchat
autogen-ext[openai]
streamlit
python-dotenv
```

## Run the App

With the virtual environment activated, run:

```powershell
streamlit run app.py
```

Streamlit should open the application in your browser. If it does not, use the local URL shown in the terminal.

## Example Questions to Try

| Department | Example question |
|---|---|
| Marketing | How can we increase market sales? |
| IT Support | My application keeps crashing. How do I fix it? |
| Finance | How do I request a refund for an invoice? |
| HR | What is the process for applying for annual leave? |

The selected department depends on the selector agent's classification and the routing logic in `app.py`.

## Workflow Limit

The app uses a maximum of **two model calls per customer question**:

1. The selector chooses the specialist.
2. The selected specialist answers.

This is an application-level limit, not a multi-agent group-chat termination condition. The app does not repeatedly cycle through agents. A termination marker in a specialist response is only a text marker; the sequential control flow is what limits the calls.

## Troubleshooting

### `ModuleNotFoundError`

Confirm that the virtual environment is activated, then run:

```powershell
pip install -r requirements.txt
```

### OpenAI API key or authentication error

- Check that `.env` exists in the project root.
- Confirm `OPENAI_API_KEY` is set correctly.
- Ensure the API key is active and your account has available quota.
- Restart Streamlit after changing `.env`.

### PowerShell cannot activate the virtual environment

Run this in the current PowerShell session:

```powershell
Set-ExecutionPolicy -Scope Process -ExecutionPolicy Bypass
.\venv\Scripts\Activate.ps1
```

### Port is already in use

Run Streamlit on another port:

```powershell
streamlit run app.py --server.port 8502
```

## Security Notes

- Keep `.env` out of version control.
- Do not put real API keys in `README.md`, screenshots, or source code.
- Share `.env.example` with placeholder values instead of sharing `.env`.

Example `.env.example`:

```env
OPENAI_API_KEY=replace_with_your_api_key
OPENAI_MODEL=gpt-4o-mini
```

## Current Limitations

- Routing depends on the selector prompt and fallback logic in `app.py`.
- The agents provide AI-generated guidance; they are not connected to company systems or verified internal policies.
- Conversation history is maintained in the Streamlit session and is not stored in a persistent database.
- API usage may incur charges.

## Possible Improvements

- Add a general-support or clarification route for questions outside the four departments.
- Add tests for routing and response parsing.
- Connect the agents to approved internal FAQs or knowledge bases.
- Add authentication, persistent conversation storage, and monitoring.
- Add feedback controls to evaluate response quality.

## License

Add a license here if you plan to publish or distribute this project.
