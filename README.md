# notes-bot
Bot for fast notes taking from telegram-bot, yandex-station, etc.

## Implemented service integrations
### Chats:
- Telegram (https://core.telegram.org/bots/api#authorizing-your-bot)
### Notes:
- Teamly (https://academy.teamly.ru/space/5019017b-ad03-4c00-bdc0-0952fc1cac88/article/dfa9a32d-02c8-4f35-95d9-c98ca2e478c0)
- Yonote (https://yonote.ru/developers#section/Vvedenie)
- Notion (https://developers.notion.com/reference/intro)

#### Minimal notes structure you need:
- title: [string] note text
- status: [string] from list of values, for example "in progress", "new", "done"
- done: [bool] checkbox for autodeleting

### Config
Copy config.example.yaml to config.yaml and fill in with your values.
Two filter modes:
  1. If no one note application config with start_words value exists, all notes are duplicated in all configured applications
  2. Else, messages starting with start_words are sent to this application, other messages to applications with an empty start_words

## To-do
1. Many users with their own configs from chat:
  - where do you want to save your notes (Teamly, Yonote, ...);
  - delete messages after save or not.
2. Sberchat support. One user for all chat-bots.
3. Yandex-station support.
