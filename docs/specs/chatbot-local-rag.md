# Local RAGtaurant Chatbot

## Problem Statement

The current chatbot combines RAG, tool calls, conversation history, and reservation operations in a difficult-to-control flow. Some tools access MongoDB directly and bypass the API's authorization rules; weather forecasts are not connected to the agent; and responses rely too heavily on the model following instructions not to invent data or execute changes without confirmation. Customers need a reliable assistant limited to restaurant-related tasks and consistent with menu, weather, and reservation rules.

## Solution

Refactor the React/FastAPI chatbot so it responds only in Spanish using authorized restaurant sources, Open-Meteo results, and the reservation API. Use small tools with clear boundaries, retrieve structured menu data for dietary and allergen queries, validate reservation operations deterministically, and require confirmation before any mutation. Keep Ollama and chatbot processing local; Open-Meteo requires an internet connection.

The chatbot will handle restaurant information, the menu, allergies and dietary needs, weather forecasts, and reservation creation, lookup, changes, and cancellation. It must clearly decline requests outside this scope or answer that it lacks sufficient evidence. Conversations must be isolated per browser tab and not permanently persisted.

## User Stories

1. As a customer, I want to ask in Spanish about the restaurant's location, hours, and services so I can plan my visit using reliable information.
2. As a customer, I want the assistant to consult only authorized restaurant sources so I do not receive invented or generic information.
3. As a customer, I want the assistant to say when it cannot find an answer so I can verify the information elsewhere.
4. As a customer, I want the assistant to decline requests unrelated to the restaurant so the chatbot stays focused.
5. As a customer, I want to search for dishes by name, ingredients, category, and price so I can find suitable options.
6. As a vegetarian or vegan customer, I want results to use the dietary labels recorded for menu items so they do not depend on model inference.
7. As a customer with allergies, I want to filter dishes using their explicitly recorded allergens so I can identify options using verifiable information.
8. As a customer with allergies, I want the assistant not to guarantee the absence of cross-contamination when that information is unavailable so I understand the limits of the available data.
9. As a customer, I want to ask about the weather over the coming days so I can plan a restaurant visit.
10. As a customer, I want to ask about a specific date and receive a forecast only if it falls between today and the next 13 days so I am not given invented predictions.
11. As a customer with a reservation verified in the conversation, I want to ask about the weather on its date without repeating the date so I can get a contextual answer.
12. As a customer, I want to create a reservation by providing my name, email, phone number, date, time, and party size so I can book a table through conversation.
13. As a customer, I want to change my reservation date, time, or party size so I can update my visit without making another reservation.
14. As a customer, I want to look up a reservation using its code, email, and phone number so I can review its details without exposing someone else's reservation.
15. As a customer, I want to cancel a verified reservation so I can release my table if I cannot attend.
16. As a customer, I want the assistant to summarize a creation, change, or cancellation and wait for my explicit confirmation so accidental changes are prevented.
17. As a customer, I want to book again for the same day after canceling so I can change my plans without losing the option to visit.
18. As a customer, I want reservations accepted only from today through the next 13 days, in half-hour slots between 12:00 and 23:00, so I can book valid times.
19. As a customer, I want each browser tab to have an isolated conversation so my history is not mixed with another person's.
20. As a customer, I want conversation context not to be stored permanently so my messages have limited retention.
21. As a project operator, I want to choose the LLM and embeddings using local quality, latency, and memory measurements so I can balance accuracy and hardware requirements.
22. As a project operator, I want to evaluate the model on CPU and on the NVIDIA RTX 5070 Ti with 12 GB of VRAM when it is available so I can compare both modes without requiring a system restart as part of this work.

## Implementation Decisions

- Keep Ollama, the LLM, and chat history storage local. Open-Meteo is an external service and requires internet access.
- Initially evaluate Qwen3 8B for generation and tool calling with BGE-M3 for multilingual embeddings. Compare it with Llama 3.2 3B as a smaller alternative; do not make a final selection without benchmarking against the restaurant data and hardware.
- Changing the embedding model requires regenerating all vectors with the same model used for query embeddings and aligning the vector index dimension. Evaluation candidates have different dimensions.
- Use the LLM as a conversational coordinator, not as the source of truth. Menu and dietary/allergen rules must be checked against structured menu attributes; institutional RAG responses must use retrieved content only.
- Limit the agent to explicit tools for menu search, restaurant information, weather, and reservation operations. Do not allow general-purpose tasks or unrestricted database access.
- Reservation tools must reuse reservation service rules rather than querying or mutating MongoDB directly. Access to an existing reservation requires matching reservation code, email, and phone number.
- Enforce confirmation in the backend, not only in the prompt. Before creating, changing, or canceling a reservation, the chatbot presents a summary; no mutation occurs until an affirmative response is received for that pending action.
- A reservation consists of a name, email, phone number, date, time, and party size. Chatbot changes may update only the date, time, and party size; contact details and the name cannot be changed through the chatbot.
- Validate reservation dates in the restaurant's time zone: today (day 1) through today + 13 days (day 14), inclusive. For today, the requested time must still be available. Valid times are every half hour from 12:00 through 23:00, inclusive.
- Cancellation retains the reservation with a canceled status. Only active reservations prevent the same contacts from making another reservation for the same day, so rebooking that day is allowed. The retention policy for canceled records must be defined before production use with real customers.
- Weather forecasts use the restaurant's configured location and cover a 14-day horizon. The bot may answer for an explicit date in that horizon, the next few days, or a date from a reservation verified in the conversation. It must not report past dates or dates outside the horizon; provider errors or unavailable forecasts must be reported without inventing values.
- Generate a random history identifier per browser tab. History is ephemeral and not permanently stored; restarting the backend clears it.
- Keep the existing chat widget as the interface. A separate reservation-management interface is out of scope.

## Testing Decisions

- Test observable behavior rather than agent implementation details: final response, refusal when evidence is missing or a request is out of scope, selected tools, and actual reservation state.
- Use the chat HTTP boundary as the primary integration seam. Replace Ollama, Open-Meteo, and other external providers with deterministic doubles; verify that a conversation retains confirmation state without persisting it.
- Add cases for menu and institutional questions with and without evidence; dietary/allergen answers based on structured data; forecasts for today, the final day of the 14-day horizon, past dates, dates outside the horizon, and provider failures.
- Test reservation creation, lookup, changes, and cancellation; authorization using reservation code/email/phone; confirmation prompts; no mutation before an affirmative answer; date-window and half-hour validation; and rebooking on the same day after cancellation.
- Extend existing reservation model and service tests and API contract tests for cancellation and indexes. Add real MongoDB integration tests for active-reservation uniqueness and rebooking after cancellation, following the existing integration-test style.
- Add frontend tests for per-tab session isolation, conversation continuity, and rendering confirmation requests and responses. The project does not currently have a frontend testing framework.
- Evaluate LLM and embedding candidates outside CI using a versioned set of Spanish questions about real restaurant data. Measure tool-calling accuracy, grounding, retrieval, latency, and memory on CPU and, when available, GPU; include unanswerable questions and do not perform real mutations.

## Out of Scope

- Responses in languages other than Spanish.
- General questions unrelated to the restaurant, unrestricted web browsing, or unauthorized sources.
- Medical guarantees or assurances about cross-contamination not supported by restaurant information.
- Strong authentication using one-time passwords, SMS, email, or another provider; existing operations use the reservation code/email/phone.
- Permanent conversation persistence or history synchronization across tabs/devices.
- A reservation interface separate from the chatbot.
- Cloud deployment, remote inference, or replacing Ollama.

## Further Notes

- The current Open-Meteo service returns seven days and must expose the required 14 dates.
- The current agent binds tools directly, and reservation tools access MongoDB directly; these must be migrated to respect shared rules.
- The repository has a default LLM value that differs from the value in Docker Compose; configuration must be made consistent and the effective model documented.
- Docker Compose requests an NVIDIA GPU. During implementation, `nvidia-smi` detected the NVIDIA GeForce RTX 5070 Ti Laptop GPU with 12,227 MiB of VRAM on the host and inside the Ollama container; no restart was needed.
- This specification was approved in conversation; its associated GitHub issue is the reference for execution and tracking.
