"use client";

import Link from "@tiptap/extension-link";
import { EditorContent, useEditor } from "@tiptap/react";
import StarterKit from "@tiptap/starter-kit";
import { useEffect } from "react";

import {
  TipTapDocumentSchema,
  type TipTapDocument,
} from "@/lib/proposalApi";

import ProposalEditorToolbar from "./ProposalEditorToolbar";

interface ProposalSectionEditorProps {
  document: TipTapDocument;
  editable: boolean;
  onChange: (document: TipTapDocument) => void;
}

export default function ProposalSectionEditor({
  document,
  editable,
  onChange,
}: ProposalSectionEditorProps) {
  const editor = useEditor({
    immediatelyRender: false,
    extensions: [
      StarterKit.configure({
        heading: { levels: [1, 2, 3] },
        link: false,
      }),
      Link.configure({
        protocols: ["http", "https", "mailto"],
        HTMLAttributes: {
          rel: "noopener noreferrer nofollow",
          target: "_blank",
        },
      }),
    ],
    content: document,
    editable,
    editorProps: {
      attributes: {
        class:
          "min-h-[420px] px-6 py-5 text-sm leading-7 text-slate-200 outline-none [&_h1]:text-3xl [&_h2]:text-2xl [&_h3]:text-xl [&_h1]:font-bold [&_h2]:font-bold [&_h3]:font-semibold [&_ul]:list-disc [&_ol]:list-decimal [&_ul]:pl-6 [&_ol]:pl-6 [&_blockquote]:border-l-2 [&_blockquote]:border-emerald [&_blockquote]:pl-4",
        "aria-label": "Proposal section editor",
      },
    },
    onUpdate: ({ editor: currentEditor }) => {
      const parsed = TipTapDocumentSchema.safeParse(currentEditor.getJSON());
      if (parsed.success) onChange(parsed.data);
    },
  });

  useEffect(() => {
    editor?.setEditable(editable);
  }, [editable, editor]);

  useEffect(() => {
    if (!editor) return;
    const current = JSON.stringify(editor.getJSON());
    const incoming = JSON.stringify(document);
    if (current !== incoming) {
      editor.commands.setContent(document, { emitUpdate: false });
    }
  }, [document, editor]);

  return (
    <div className="overflow-hidden rounded-xl border border-white/10 bg-background/50">
      <ProposalEditorToolbar editor={editor} disabled={!editable} />
      <EditorContent editor={editor} />
    </div>
  );
}
