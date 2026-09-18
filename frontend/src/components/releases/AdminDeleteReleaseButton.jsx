import React, { useState } from "react";
import { Loader2, Trash2 } from "lucide-react";
import { api, formatApiError } from "@/api/client";
import { useAuth } from "@/api/AuthContext";
import { toast } from "@/components/ui/sonner";
import {
  AlertDialog, AlertDialogTrigger, AlertDialogContent, AlertDialogHeader,
  AlertDialogTitle, AlertDialogDescription, AlertDialogFooter, AlertDialogCancel,
} from "@/components/ui/alert-dialog";

export const AdminDeleteReleaseButton = ({ release, onDeleted, compact = false }) => {
  const { hasPermission } = useAuth();
  const [open, setOpen] = useState(false);
  const [deleting, setDeleting] = useState(false);
  const [error, setError] = useState("");
  const testId = compact ? `admin-release-delete-${release.id}` : "admin-release-detail-delete";

  if (!hasPermission("releases.delete") || !["draft", "rejected"].includes(release.status)) return null;

  const handleDelete = async () => {
    if (deleting) return;
    setDeleting(true);
    setError("");
    try {
      await api.delete(`/admin/releases/${release.id}`);
    } catch (requestError) {
      setError(formatApiError(requestError.response?.data?.detail) || "Gagal menghapus rilisan. Silakan coba lagi.");
      setDeleting(false);
      return;
    }
    setDeleting(false);
    setOpen(false);
    toast.success("Rilisan berhasil dihapus.");
    onDeleted(release.id);
  };

  return (
    <AlertDialog open={open} onOpenChange={(value) => { if (!deleting) { setOpen(value); setError(""); } }}>
      <AlertDialogTrigger asChild>
        <button
          type="button" data-testid={testId}
          title={`Hapus rilisan ${release.release_title}`} aria-label={`Hapus rilisan ${release.release_title}`}
          className={`relative z-10 inline-flex shrink-0 items-center justify-center gap-2 rounded-md border border-red-400/30 bg-red-500/10 text-red-300 transition-colors hover:border-red-400/60 hover:bg-red-500/20 hover:text-red-200 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-red-400 ${compact ? "h-9 w-9" : "min-h-10 px-3 py-2 text-sm font-semibold"}`}
        >
          <Trash2 className="h-4 w-4" aria-hidden="true" />
          {!compact && "Hapus Rilisan"}
        </button>
      </AlertDialogTrigger>
      <AlertDialogContent className="w-[calc(100%-2rem)] max-w-lg rounded-lg border-white/15 bg-zinc-950 text-white" data-testid={`${testId}-dialog`}>
        <AlertDialogHeader className="min-w-0 text-left">
          <AlertDialogTitle data-testid={`${testId}-title`}>Hapus rilisan?</AlertDialogTitle>
          <AlertDialogDescription className="break-words text-zinc-400" data-testid={`${testId}-description`}>
            Rilisan <strong className="text-zinc-200">“{release.release_title}”</strong> beserta track dan berkasnya akan dihapus permanen. Tindakan ini tidak dapat dibatalkan.
          </AlertDialogDescription>
        </AlertDialogHeader>
        {error && <div role="alert" className="break-words rounded-md bg-red-500/10 p-3 text-sm text-red-300" data-testid={`${testId}-error`}>{error}</div>}
        <AlertDialogFooter>
          <AlertDialogCancel disabled={deleting} className="border-white/15 bg-transparent text-zinc-200 hover:bg-white/10 hover:text-white" data-testid={`${testId}-cancel`}>Batal</AlertDialogCancel>
          <button type="button" onClick={handleDelete} disabled={deleting} aria-busy={deleting}
            className="inline-flex min-h-10 items-center justify-center gap-2 rounded-md bg-red-600 px-4 py-2 text-sm font-semibold text-white transition-colors hover:bg-red-500 disabled:cursor-wait disabled:opacity-60"
            data-testid={`${testId}-confirm`}>
            {deleting ? <Loader2 className="h-4 w-4 animate-spin" aria-hidden="true" /> : <Trash2 className="h-4 w-4" aria-hidden="true" />}
            {deleting ? "Menghapus…" : "Hapus Rilisan"}
          </button>
        </AlertDialogFooter>
      </AlertDialogContent>
    </AlertDialog>
  );
};