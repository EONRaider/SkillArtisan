/** Generate <available_skills> XML prompt block for agent system prompts. */
import * as path from "node:path";
import { findSkillMd, readProperties } from "./parser.js";
/** Generate the <available_skills> XML block for inclusion in agent prompts.
 *
 * This XML format is what Anthropic uses and recommends for Claude models.
 * Skill Clients may format skill information differently to suit their
 * models or preferences.
 *
 * @param skillDirs - List of paths to skill directories
 * @returns XML string with <available_skills> block containing each skill's
 *          name, description, and location.
 *
 * @example
 * ```ts
 * const result = toPrompt(["/path/to/skill-a", "/path/to/skill-b"]);
 * console.log(result);
 * // <available_skills>
 * // <skill>
 * // <name>pdf-reader</name>
 * // <description>Read and extract text from PDF files</description>
 * // <location>/path/to/pdf-reader/SKILL.md</location>
 * // </skill>
 * // </available_skills>
 * ```
 */
export async function toPrompt(skillDirs) {
    if (skillDirs.length === 0) {
        return "<available_skills>\n</available_skills>";
    }
    const lines = ["<available_skills>"];
    for (const skillDir of skillDirs) {
        const resolvedDir = path.resolve(skillDir);
        const props = await readProperties(resolvedDir);
        lines.push("<skill>");
        lines.push("<name>");
        lines.push(escapeHtml(props.name));
        lines.push("</name>");
        lines.push("<description>");
        lines.push(escapeHtml(props.description));
        lines.push("</description>");
        const skillMdPath = await findSkillMd(resolvedDir);
        lines.push("<location>");
        lines.push(skillMdPath ?? "");
        lines.push("</location>");
        lines.push("</skill>");
    }
    lines.push("</available_skills>");
    return lines.join("\n");
}
/** Escape HTML special characters. */
function escapeHtml(text) {
    return text
        .replace(/&/g, "&amp;")
        .replace(/</g, "&lt;")
        .replace(/>/g, "&gt;")
        .replace(/"/g, "&quot;")
        .replace(/'/g, "&#39;");
}
//# sourceMappingURL=prompt.js.map