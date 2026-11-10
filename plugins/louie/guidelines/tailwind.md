# Tailwind

For styling with Tailwind CSS: the choices where more than one would be reasonable. These are
defaults for new code: in an existing codebase, its documented conventions and the pattern its
code already follows win.

## 1. Theme tokens, never raw values

- Colors, spacing, radii and fonts come from the theme: `bg-surface`, `text-on-surface`,
  `rounded-md`. No palette color (`bg-gray-100`), `text-white`, hex, `style="color: …"` or
  arbitrary `[#1a1a1a]` in a component.
- A color is chosen as a pair: a background with the text token made for it (`bg-warning` with
  `text-on-warning`). A text color picked alone fails on another background or theme.
- A value the theme lacks goes into the theme, named for its role, not into one component.
  An arbitrary value (`w-[37px]`) is the exception, for a size nothing else shares.

**Test:** a search of the changed files for palette colors, hex and `[#` finds nothing.

## 2. Dark mode through the tokens

- A token switches with the theme, so a component written with tokens needs no `dark:` of its own.
  A `dark:` variant is for what the tokens can't express, and stays rare.
- Check every change in both themes, and its hover, focus, disabled and error states: these are
  where contrast breaks first.
- Text meets WCAG AA contrast (4.5:1, 3:1 for large text) on its background, in both themes. A
  keyboard focus is always visible: `focus-visible:` rings, never `outline-none` alone.

**Test:** the changed screen reads correctly in light and dark, with the keyboard too.

## 3. Class names Tailwind can see

- Write every class name whole. Tailwind finds classes by scanning the source, so
  `` `bg-${tone}-500` `` is never generated; map each value to a full name:
  `{ error: 'bg-error', ok: 'bg-success' }[tone]`.
- A component that takes a `class` merges it through `cn()` (`tailwind-merge` with `clsx`), so the
  caller's class wins over the component's default instead of fighting it.
- Variants (size, tone, state) come from `cva`, not from ternaries in the template.
- The class order is the formatter's (`prettier-plugin-tailwindcss`); don't sort by hand.

**Test:** no class name is built from pieces, and every component that takes `class` merges it.

## 4. Configuration

- Tailwind 4 is configured in CSS: the theme in `@theme`, plugins with `@plugin`, variants with
  `@custom-variant`. A new project has no `tailwind.config.js`.
- `@apply` belongs in the base layer only (elements, third-party markup); a component uses classes
  in its template.

**Test:** every theme value is defined once, in the CSS the app imports.
