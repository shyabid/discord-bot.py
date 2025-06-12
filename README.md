# Jotaro - Open Source Discord Bot

Welcome to **Jotaro**, a versatile and powerful open-source Discord bot designed to enhance server experience through a rich suite of features. Developed with modularity, privacy, and community-driven improvements at its core, Jotaro is your reliable companion for everything from moderation and fun interactions to utility commands and personalized automation.

---

## Overview

Jotaro is built with the `discord.py` framework, leveraging modern Python async capabilities for smooth, scalable performance across multiple servers. Its architecture is thoughtfully segmented into plugins—each encapsulating focused functionality—allowing for easy extension, customization, and maintenance.

At its heart, Jotaro seamlessly integrates with an SQLite database via a dedicated database manager to store persistent data securely and efficiently. This design ensures fast access, consistency, and straightforward deployment without heavy infrastructure requirements.

---

## Features

- **Dynamic command prefixing per server**  
- **Comprehensive moderation tools**  
- **Automated reminders and leveling systems**  
- **Entertainment commands including quizzes, waifu-related features, and fun games**  
- **Audio control and voice channel utilities**  
- **Robust error handling with developer notifications**  
- **Fine-grained permissions and cooldown management**  
- **Extensible plugin system for effortless feature scaling**

---

## Architecture & Key Components

### Core Files

- **bot.py**  
  The central bot class, extending `AutoShardedBot` to optimize multi-guild operations. Handles command prefix resolution, plugin loading, event hooks (ready, errors, completions), and integrates the database manager. It’s the foundation upon which all features are built and coordinated.

- **db_manager.py**  
  Manages SQLite interactions, encapsulating schema setup, queries, and updates. This ensures data integrity and isolates database logic from command implementations, fostering maintainability and reliability.

- **main.py**  
  Entrypoint that initializes and launches the bot instance. Keeps startup procedures clean and focused.

- **utils.py**  
  Helper functions utilized across plugins for common tasks, promoting code reuse and clarity.

- **data.py**  
  Contains static data or configuration mappings that multiple plugins reference, supporting consistency.

- **schema.sql**  
  Defines the database schema to structure persistent storage, carefully designed to cover features like prefixes, user stats, reminders, and more.

- **waifu_list_final.json**  
  A comprehensive dataset powering the “waifu” themed plugin, enabling fun user interactions with pre-curated content.

---

### Plugins

The plugins folder hosts modular features, each as a cog loaded dynamically by the bot:

- **afk.py** — Manages AFK statuses, allowing users to set and track when they are away.  
- **alias.py** — Provides command aliasing to simplify user experience.  
- **anime.py** — Adds anime-themed commands, connecting the bot to popular fandom interactions.  
- **audio.py** — Controls music and voice channel functionalities, enabling voice interactions.  
- **auto.py** — Automates routine tasks for server management.  
- **bookmark.py** — Allows users to bookmark messages or content for later.  
- **botto.py** — Contains meta commands related to bot info and stats.  
- **economy.py** — Implements an in-server economy system with virtual currency and transactions.  
- **fun.py** — Collection of entertainment commands to keep the community engaged.  
- **goblet.py** — Specialized plugin for themed games or contests.  
- **help.py** — Custom help command presenting command information neatly.  
- **holy.py** — Adds themed commands with spiritual or humorous undertones.  
- **interactions.py** — Handles buttons, dropdowns, and other Discord interactions.  
- **leveling.py** — Tracks user activity to reward leveling and engagement.  
- **meta.py** — Meta commands for managing plugins and bot internals.  
- **misc.py** — Miscellaneous commands that don’t fit elsewhere.  
- **mod.py** — Core moderation tools like kick, ban, mute, etc.  
- **news.py** — Integrates news or announcements delivery within servers.  
- **prefix.py** — Enables server-specific prefix configuration.  
- **purge.py** — Bulk message deletion command for moderation.  
- **quiz.py** — Interactive quiz games for engagement and fun.  
- **reminder.py** — User reminders and timed notifications.  
- **snipe.py** — Recalls recently deleted or edited messages.  
- **tags.py** — Custom tags for server-specific quick info snippets.  
- **ungrouped.py** — Commands that are still in development or don’t belong to a category yet.  
- **vccontrol.py** — Voice channel controls and management commands.  
- **waifu.py** — “Waifu” themed interactions powered by the JSON dataset.  
- **welcomer.py** — Welcomes new members with configurable messages.

---

## Privacy & Compliance

Jotaro is committed to respecting user privacy and operates in full accordance with EU GDPR and related regulations. Key privacy-conscious design decisions include:

- **Minimal data collection:** Only essential information for bot functionality is stored, such as server settings, user levels, and command usage statistics. No personal data beyond what users voluntarily provide is kept.  
- **Secure data handling:** All persistent data is stored locally in SQLite databases without external data sharing.  
- **Transparency:** Bot commands and interactions never expose sensitive data publicly or to third parties.  
- **User control:** Users can manage their own data, such as resetting levels or removing reminders.  
- **Compliance-ready:** Code and practices align with best-practice guidelines for data protection and user consent.

This privacy foundation allows server owners and users to confidently deploy Jotaro without compromising their members’ data rights.

---

## Why Open Source?

Open sourcing Jotaro invites collaboration, transparency, and continuous improvement. Benefits include:

- **Community-driven enhancements**: Anyone can contribute features, bug fixes, or optimizations.  
- **Transparency**: Users can audit the code for security and privacy guarantees.  
- **Customization**: Servers can tailor the bot to their exact needs by modifying or extending plugins.  
- **Learning resource**: Aspiring developers can study a real-world, scalable bot architecture.  
- **Sustainability**: Open collaboration ensures long-term project maintenance beyond individual developers.

Jotaro exemplifies how open-source software can empower communities through shared ownership and collective expertise.

---

## Getting Started

1. Clone the repository.  
2. Set up a Discord bot application and obtain your bot token.  
3. Configure `.env` with your token, owner ID, and desired description.  
4. Install dependencies from `requirements.txt`.  
5. Run `main.py` to launch the bot.  
6. Customize your server prefixes and load/unload plugins as needed.

For detailed configuration options and commands, please refer to the individual plugin documentation within the codebase.

---

Thank you for exploring Jotaro! Whether you are a server admin, developer, or enthusiast, this project welcomes your involvement.
