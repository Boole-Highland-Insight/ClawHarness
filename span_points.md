**如果你想手工在新装的 OpenClaw 里重打**
我建议只打这批最关键的锚点。

文件和 span 名字：

- `src/gateway/server-methods/chat.ts`
  - `chat_send_span`
  - `ack`
  - `dispatch_start`

- `src/infra/agent-wait-span.ts`
  - 事件名：`agent_wait_span`
  - phase：
    - `wait_start`
    - `wait_cache_hit`
    - `wait_race_start`
    - `wait_first_source`
    - `wait_complete`
    - `lifecycle_terminal`
    - `dedupe_terminal_write`

- `src/gateway/server-methods/agent.ts`
  - 在 `agent.wait` 入口、cache hit、race start、first source、complete 处发 `agent_wait_span`

- `src/gateway/server-methods/agent-wait-dedupe.ts`
  - 在 dedupe 写终态时发 `dedupe_terminal_write`

- `src/agents/pi-embedded-subscribe.handlers.lifecycle.ts`
  - 在 agent `end/error` 时发 `lifecycle_terminal`

- `src/auto-reply/reply/reply-dispatcher.ts`
  - 事件名：`reply_dispatch_span`
  - phase：
    - `queue_enter`
    - `queue_acquired`
    - `queue_idle`
    - `queue_complete`

- `src/agents/pi-embedded-span.ts`
  - 事件名：`embedded_run_span`

- `src/agents/pi-embedded-runner/run.ts`
  - `queue_enter`
  - `queue_acquired`

- `src/agents/pi-embedded-runner/run/attempt.ts`
  - `prompt_build_start`
  - `prompt_start`
  - `prompt_end`

- `src/agents/pi-embedded-subscribe.handlers.messages.ts`
  - `assistant_message_start`

这套已经足够把：
`chat.send -> wait -> embedded queue -> prompt build -> first assistant output -> terminal write`
这一整条链拆开。
