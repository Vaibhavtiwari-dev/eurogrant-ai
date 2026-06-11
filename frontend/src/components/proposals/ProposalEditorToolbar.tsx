"use client";

import type { Editor } from "@tiptap/react";

interface ProposalEditorToolbarProps {
  editor: Editor | null;
  disabled: boolean;
}

export default function ProposalEditorToolbar({
  editor,
  disabled,
}: ProposalEditorToolbarProps) {
  if (!editor) return null;

  const actions = [
    {
      label: "Bold",
      active: editor.isActive("bold"),
      run: () => editor.chain().focus().toggleBold().run(),
    },
    {
      label: "Italic",
      active: editor.isActive("italic"),
      run: () => editor.chain().focus().toggleItalic().run(),
    },
    {
      label: "Heading",
      active: editor.isActive("heading", { level: 2 }),
      run: () => editor.chain().focus().toggleHeading({ level: 2 }).run(),
    },
    {
      label: "Bullets",
      active: editor.isActive("bulletList"),
      run: () => editor.chain().focus().toggleBulletList().run(),
    },
    {
      label: "Numbered",
      active: editor.isActive("orderedList"),
      run: () => editor.chain().focus().toggleOrderedList().run(),
    },
    {
      label: "Quote",
      active: editor.isActive("blockquote"),
      run: () => editor.chain().focus().toggleBlockquote().run(),
    },
  ];

  return (
    <div className="flex flex-wrap gap-2 border-b border-white/10 p-3" role="toolbar">
      {actions.map((action) => (
        <button
          key={action.label}
          type="button"
          aria-label={action.label}
          aria-pressed={action.active}
          disabled={disabled}
          onClick={action.run}
          className={`rounded-md border px-3 py-1.5 text-xs font-semibold transition ${
            action.active
              ? "border-emerald/50 bg-emerald/15 text-emerald-light"
              : "border-white/10 bg-white/5 text-slate-300 hover:bg-white/10"
          } disabled:cursor-not-allowed disabled:opacity-40`}
        >
          {action.label}
        </button>
      ))}
    </div>
  );
}
