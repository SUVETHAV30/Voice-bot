# Voice ADK

## Installation

```bash 
pip install poetry
poetry install 
```

before running check 

`.env.example` and write it in `.env`


and run the `dev` server for livekit-agent 

```bash
poetry run python agent.py dev
```

copy `id` to `sandbox-id` of react sdk (.env.local) and aslo `livekit-url`

```bash
cd agent-starter-react
```

```bash
npm run dev
```

#### Note Now we will have 2 services running livekit agent and react sdk

```
open http://localhost:3000
```
