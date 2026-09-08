# Connecting the prompts

| File | Where to use it |
|---|---|
| [urbanomy-specialist.md](urbanomy-specialist.md) | System instructions for an external LLM specialist with Urbanomy MCP tools |
| [urbanomy-routing.md](urbanomy-routing.md) | An instruction section for the main orchestrator with a connected delegation or A2A tool |
| [optimizer-strategy.txt](optimizer-strategy.txt) | Contents of the `strategy` field in a specific optimization request |

The server does not load these files automatically. The Urbanomy A2A service executes
structured calculation requests; it does not support installing the specialist prompt.
The specialist prompt is for an external agent that operates the MCP tools.

When configuring the orchestrator, bind the specialist to an actual delegation tool:
its name and schema come from your runtime configuration. This repository has no verified
Synapse delegation tool name, so none is specified here. Describe the economic tasks
and the procedure for continuing jobs in the connected tool's description.
The router must have access to that schema, not just text saying that a specialist exists.

The runtime must retain task parameters, mode, transport, returned ID, and status across
turns; schedule polling; and bound the total waiting time. The recommended polling
interval for long jobs is 10–15 seconds. If resumption is unavailable, the agent returns
the current status and ID without promising a later notification.
This repository does not implement the external orchestrator's scheduler.

Supply demo parameters separately from the [examples](../examples/integration/README.md).
The `strategy` field requires the actual text, not a file path. JSON requests contain
a copy for standalone use; when changing the strategy, synchronize both optimization
MCP requests and their A2A envelopes. Saved results from previous runs are historical
records and must not be edited retroactively.

The scorer's response format (`{"score": number}`), the 0–1 range, and error handling
are defined in code. The user strategy defines the evaluation criterion.
New scoring scales, group weights, and social indicators require domain agreement;
this package does not invent them.

Run the [agent behavior evaluation cases](../examples/integration/agent-evals.md)
separately; do not include them in system instructions. API tests and saved calculations
do not evaluate how an LLM selects tools.
