#!/usr/bin/env node
/** CLI for skills-ref library. */
import { Command } from "commander";
import { statSync } from "node:fs";
import * as path from "node:path";
import { version } from "./index.js";
import { SkillError } from "./errors.js";
import { readProperties } from "./parser.js";
import { toPrompt } from "./prompt.js";
import { validate } from "./validator.js";
/** Check if path points directly to a SKILL.md or skill.md file. */
function isSkillMdFile(filePath) {
    try {
        const stats = statSync(filePath, { throwIfNoEntry: false });
        if (stats?.isFile()) {
            const baseName = path.basename(filePath).toLowerCase();
            return baseName === "skill.md";
        }
        return false;
    }
    catch {
        return false;
    }
}
const program = new Command();
program.version(version).description("Reference library for Agent Skills");
program
    .command("validate")
    .argument("<skill_path>", "Path to skill directory or SKILL.md file")
    .action(async (skillPath) => {
    /** Validate a skill directory.
     *
     * Checks that the skill has a valid SKILL.md with proper frontmatter,
     * correct naming conventions, and required fields.
     *
     * Exit codes:
     *   0: Valid skill
     *   1: Validation errors found
     */
    let skillDir = skillPath;
    if (isSkillMdFile(skillPath)) {
        skillDir = path.dirname(skillPath);
    }
    const errors = await validate(skillDir);
    if (errors.length > 0) {
        console.error(`Validation failed for ${skillDir}:`);
        for (const error of errors) {
            console.error(`  - ${error}`);
        }
        process.exit(1);
    }
    else {
        console.log(`Valid skill: ${skillDir}`);
    }
});
program
    .command("read-properties")
    .argument("<skill_path>", "Path to skill directory or SKILL.md file")
    .action(async (skillPath) => {
    /** Read and print skill properties as JSON.
     *
     * Parses the YAML frontmatter from SKILL.md and outputs the
     * properties as JSON.
     *
     * Exit codes:
     *   0: Success
     *   1: Parse error
     */
    try {
        let skillDir = skillPath;
        if (isSkillMdFile(skillPath)) {
            skillDir = path.dirname(skillPath);
        }
        const props = await readProperties(skillDir);
        console.log(JSON.stringify(props.toDict(), null, 2));
    }
    catch (e) {
        if (e instanceof SkillError) {
            console.error(`Error: ${e.message}`);
        }
        else {
            console.error(`Error: ${String(e)}`);
        }
        process.exit(1);
    }
});
program
    .command("to-prompt")
    .argument("<skill_paths...>", "Paths to skill directories")
    .action(async (skillPaths) => {
    /** Generate <available_skills> XML for agent prompts.
     *
     * Accepts one or more skill directories.
     *
     * Exit codes:
     *   0: Success
     *   1: Error
     */
    try {
        const resolvedPaths = [];
        for (const skillPath of skillPaths) {
            if (isSkillMdFile(skillPath)) {
                resolvedPaths.push(path.dirname(skillPath));
            }
            else {
                resolvedPaths.push(skillPath);
            }
        }
        const output = await toPrompt(resolvedPaths);
        console.log(output);
    }
    catch (e) {
        if (e instanceof SkillError) {
            console.error(`Error: ${e.message}`);
        }
        else {
            console.error(`Error: ${String(e)}`);
        }
        process.exit(1);
    }
});
program.parse();
//# sourceMappingURL=cli.js.map