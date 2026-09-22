/** Generate <available_skills> XML prompt block for agent system prompts. */
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
export declare function toPrompt(skillDirs: string[]): Promise<string>;
//# sourceMappingURL=prompt.d.ts.map