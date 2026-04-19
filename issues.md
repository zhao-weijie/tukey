## (bug) Replacing expired key breaks existing configurations
### Severity: Major
Problem: When a key expires, a provider has to be deleted for the new key to be added and the existing configurations break.

Proposed Solution: Add an "edit" feature for keys so that we can replace the key without deleting the provider. Warn user when removing providers about potential effects with a focus modal overlay plus confirm or cancel button choices.

## (bug) Tool call element in ResponseCard.tsx is duplicated in streaming status

Symptom: tool call element is duplicated once (2 elements per tool call) shown when streaming results. When streaming finishes, the extra tool calls disappear.

## (bug) dialog.tsx elements overflow the container when state changes

Symptom: Elements fit within the container width on first load. However, after Searching (for the SearchDialog) and Testing (for the Mcpserversetup), the buttons and text input boxes bleed past the right boundary of the container.

![Sceenshot](./.testing_images/dialogbug.png)

## (improvement) Allow per-model manual retries and additional responses
Priority: high
Problem: Some models fail while others succeed sometimes due to model quality or API/provider issues. It is not currently possible to retry just for the failed models.

The first successful response should be shown as default.

## (improvement) More flexible model/provider/config in a particular configuration "slot" instead of deleting
Priority: normal

## (improvement) Tool Choice and Response Format options in Model Config do not have a "broadcast" option
Priority: normal
## (improvement) Allow individual response cards to be expanded in width for easier reading of long responses
Priority: high

As a user I want to be able to expand individual response cards to make it easier to read long responses.  

## (improvement) Response card layout and comparison UX
Priority: normal

As a user I want to be able to choose which response cards are next to each other so that I can easily compare 2 models' responses side by side.

As a user I want to choose which response cards are currently visible so that I can focus on comparing the responses I care about most.

## (improvement) Stack past responses instead of showing all ResponseCards
Priority: normal

Idea: stack and show only the first pinned response or the one with the most positive annotations for past turns. Only current turn responses are shown in full. This reduces visual clutter. The user gets a button to expand the full Response Carousele to full width.

Related idea: this might work well together with horizontal stack-ranking where the user drags conversation ResponseCards to rank them horizontally. Drag handle rather than the entire ResponseCard component as target should be easier to use.


## (improvement) Chat stats for per-model metadata in a chat
Priority: normal
As a user I want a quick view of how each model performed in the chat so that I can decide which one to use as default.  
When hovering the chat name in the top bar, a popover/dropdown appears showing the stats for each model.

Stats to include: cost, input tokens, output tokens, latency, tok/s, user ratings (positive + negative).

## (improvement) Chat input box and default chat area width for user messages should be narrower and centered.
Priority: normal
As a user I want the chat and message area to be centered in my view so that my eyes do not have to scan left and right too much, reducing eye fatigue. 

Multiple model responses are allowed to take the full width of the chat area container, since it is easier to compare responses side by side.

![Sceenshot](./.testing_images/centered_chat.png)

---
# Not relevant to the codebase, for reference only
## (bug) Antigravity bug

Symptom: Open repo in antigravity, type a prompt and send in both planning and fast mode. Switched to other repository, no change. Switched to agent manager, chat is not created. No response or thinking or any output at all. Same result even after downloading and installing latest version.
