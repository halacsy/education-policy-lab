# Agent: <name>

Version: 1
Type: <meta | expert | critic | synthesis>
Provider-role: <generator | judge>

## Role
<one sentence: what this agent is>

## Mission
<what it must achieve within a round>

## Inputs
<files / prior-step outputs it reads>

## Outputs
<files it writes, with format>

## Rules
<numbered, checkable behavioural rules>

## Evidence discipline
<how claims are tagged: strong / moderate / weak / contested / assumption;
what may never be asserted without a tag>

## Uncertainty discipline
<how uncertainty is expressed; confidence levels; "what would change my mind">

## Failure modes
<the specific ways this agent tends to fail, to be watched by critics/meta_critic>

## Self-critique questions
<questions the agent answers about its own output before finishing>

## Output template
<the exact skeleton of the agent's output>

## Directives
<!-- Appended by the improvement step; one line per directive:
- [round-NN] DIRECTIVE:<id> — <behavioural instruction> -->
