# skills-ref

[![English](https://img.shields.io/badge/English-Click-yellow)](README.md)
[![中文文档](https://img.shields.io/badge/中文文档-点击查看-orange)](README-zh.md)

Reference library for Agent Skills.

> **Note:** This library is intended for demonstration purposes only. It is not meant to be used in production.

## Installation

```bash
pnpm install
```

After installation, `skills-ref` CLI will be available.

## Usage

### CLI

```bash
# Validate a skill
skills-ref validate path/to/skill

# Read skill properties (outputs JSON)
skills-ref read-properties path/to/skill

# Generate <available_skills> XML for agent prompts
skills-ref to-prompt path/to/skill-a path/to/skill-b
```

```bash
PS C:\Users\admin> npm install -g skills-ref

added 4 packages in 2s
PS C:\Users\admin> skills-ref --help
Usage: cli [options] [command]

Reference library for Agent Skills

Options:
  -V, --version                 output the version number
  -h, --help                    display help for command

Commands:
  validate <skill_path>
  read-properties <skill_path>
  to-prompt <skill_paths...>
  help [command]                display help for command
PS C:\Users\admin> skills-ref validate F:\ai-project\skills\skills\algorithmic-art
Valid skill: F:\ai-project\skills\skills\algorithmic-art
PS C:\Users\admin>
PS C:\Users\admin> skills-ref read-properties F:\ai-project\skills\skills\algorithmic-art
{
  "name": "algorithmic-art",
  "description": "Creating algorithmic art using p5.js with seeded randomness and interactive parameter exploration. Use this when users request creating art using code, generative art, algorithmic art, flow fields, or particle systems. Create original algorithmic art rather than copying existing artists' work to avoid copyright violations.",
  "license": "Complete terms in LICENSE.txt"
}
PS C:\Users\admin> skills-ref to-prompt F:\ai-project\skills\skills\algorithmic-art
<available_skills>
<skill>
<name>
algorithmic-art
</name>
<description>
Creating algorithmic art using p5.js with seeded randomness and interactive parameter exploration. Use this when users request creating art using code, generative art, algorithmic art, flow fields, or particle systems. Create original algorithmic art rather than copying existing artists&#39; work to avoid copyright violations.
</description>
<location>
F:\ai-project\skills\skills\algorithmic-art\SKILL.md
</location>
</skill>
</available_skills>
PS C:\Users\admin>
```

### TypeScript API

```typescript
import { validate, readProperties, toPrompt } from "skills-ref";

// Validate a skill directory
const problems = await validate("my-skill");
if (problems.length > 0) {
  console.log("Validation errors:", problems);
}

// Read skill properties
const props = await readProperties("my-skill");
console.log(`Skill: ${props.name} - ${props.description}`);

// Generate prompt for available skills
const prompt = await toPrompt(["skill-a", "skill-b"]);
console.log(prompt);
```

## Development

```bash
# Build the project
pnpm build

# Run tests
pnpm test

# Format code
pnpm format

# Lint code
pnpm lint
pnpm lint:fix
```

## Agent Prompt Integration

Use `to-prompt` to generate the suggested `<available_skills>` XML block for your agent's system prompt. This format is recommended for Anthropic's models, but Skill Clients may choose to format it differently based on the model being used.

```xml
<available_skills>
<skill>
<name>
my-skill
</name>
<description>
What this skill does and when to use it
</description>
<location>
/path/to/my-skill/SKILL.md
</location>
</skill>
</available_skills>
```

The `<location>` element tells the agent where to find the full skill instructions.

## License

MIT License
