/** Skill validation logic. */
/** Validate parsed skill metadata.
 *
 * This is the core validation function that works on already-parsed metadata,
 * avoiding duplicate file I/O when called from the parser.
 *
 * @param metadata - Parsed YAML frontmatter dictionary
 * @param skillDir - Optional path to skill directory (for name-directory match check)
 * @returns List of validation error messages. Empty list means valid.
 */
export declare function validateMetadata(metadata: Record<string, unknown>, skillDir?: string): string[];
/** Validate a skill directory.
 *
 * @param skillDir - Path to the skill directory
 * @returns List of validation error messages. Empty list means valid.
 */
export declare function validate(skillDir: string): Promise<string[]>;
//# sourceMappingURL=validator.d.ts.map