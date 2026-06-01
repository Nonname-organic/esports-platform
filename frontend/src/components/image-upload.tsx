"use client";

import { useRef, useState } from "react";
import { Upload, X, Image as ImageIcon } from "lucide-react";
import { apiClient } from "@/lib/api-client";
import { cn } from "@/lib/utils";

interface ImageUploadProps {
  value: string;
  onChange: (url: string) => void;
  purpose: "team_logo" | "team_banner" | "avatar";
  label?: string;
  aspectRatio?: "square" | "banner";
  className?: string;
}

export function ImageUpload({
  value, onChange, purpose, label, aspectRatio = "square", className,
}: ImageUploadProps) {
  const [uploading, setUploading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [urlInput, setUrlInput] = useState("");
  const [showUrlInput, setShowUrlInput] = useState(false);
  const inputRef = useRef<HTMLInputElement>(null);

  const handleFile = async (file: File) => {
    if (!file.type.startsWith("image/")) {
      setError("画像ファイルを選択してください");
      return;
    }
    if (file.size > 5 * 1024 * 1024) {
      setError("5MB以下の画像を選択してください");
      return;
    }

    setError(null);
    setUploading(true);

    try {
      const formData = new FormData();
      formData.append("file", file);

      const data = await apiClient.upload<{ url: string; key: string }>(
        `/api/v1/upload/image?purpose=${purpose}`,
        formData,
      );
      onChange(data.url);
    } catch (e) {
      setError(e instanceof Error ? e.message : "アップロードに失敗しました");
    } finally {
      setUploading(false);
    }
  };

  const handleDrop = (e: React.DragEvent) => {
    e.preventDefault();
    const file = e.dataTransfer.files[0];
    if (file) handleFile(file);
  };

  const handleUrlSubmit = () => {
    if (urlInput.trim()) {
      onChange(urlInput.trim());
      setUrlInput("");
      setShowUrlInput(false);
    }
  };

  const isBanner = aspectRatio === "banner";

  return (
    <div className={className}>
      {label && <label className="mb-2 block text-sm font-medium text-slate-400">{label}</label>}

      <div
        className={cn(
          "relative overflow-hidden rounded-xl border-2 border-dashed transition-colors",
          value ? "border-white/20" : "border-white/10 hover:border-brand-500/50",
          isBanner ? "h-32" : "h-24 w-24",
        )}
        onDragOver={(e) => e.preventDefault()}
        onDrop={handleDrop}
      >
        {/* プレビュー */}
        {value ? (
          <div className="relative h-full w-full group">
            <img
              src={value}
              alt="preview"
              className="h-full w-full object-cover"
            />
            <div className="absolute inset-0 flex items-center justify-center gap-2 bg-black/50 opacity-0 group-hover:opacity-100 transition-opacity">
              <button
                type="button"
                onClick={() => inputRef.current?.click()}
                className="rounded-lg bg-white/10 p-1.5 text-white hover:bg-white/20 transition-colors"
              >
                <Upload className="h-4 w-4" />
              </button>
              <button
                type="button"
                onClick={() => onChange("")}
                className="rounded-lg bg-red-500/20 p-1.5 text-red-400 hover:bg-red-500/30 transition-colors"
              >
                <X className="h-4 w-4" />
              </button>
            </div>
          </div>
        ) : (
          <button
            type="button"
            onClick={() => inputRef.current?.click()}
            disabled={uploading}
            className="flex h-full w-full flex-col items-center justify-center gap-1.5 text-slate-500 hover:text-slate-300 transition-colors disabled:opacity-50"
          >
            {uploading ? (
              <div className="h-5 w-5 animate-spin rounded-full border-2 border-brand-500 border-t-transparent" />
            ) : (
              <>
                <ImageIcon className="h-5 w-5" />
                <span className="text-[10px]">アップロード</span>
              </>
            )}
          </button>
        )}
      </div>

      {/* エラー */}
      {error && <p className="mt-1 text-xs text-red-400">{error}</p>}

      {/* URLで指定 */}
      <div className="mt-2">
        {!showUrlInput ? (
          <button
            type="button"
            onClick={() => setShowUrlInput(true)}
            className="text-xs text-slate-600 hover:text-slate-400 transition-colors"
          >
            URLで指定する
          </button>
        ) : (
          <div className="flex items-center gap-2">
            <input
              value={urlInput}
              onChange={(e) => setUrlInput(e.target.value)}
              onKeyDown={(e) => e.key === "Enter" && (e.preventDefault(), handleUrlSubmit())}
              placeholder="https://..."
              className="flex-1 rounded-lg border border-white/10 bg-white/5 px-2.5 py-1.5 text-xs text-white placeholder-slate-600 outline-none focus:border-brand-500"
            />
            <button
              type="button"
              onClick={handleUrlSubmit}
              className="rounded-lg bg-brand-500/10 px-2.5 py-1.5 text-xs text-brand-400 hover:bg-brand-500/20 transition-colors"
            >
              設定
            </button>
            <button
              type="button"
              onClick={() => setShowUrlInput(false)}
              className="text-slate-600 hover:text-white transition-colors"
            >
              <X className="h-3.5 w-3.5" />
            </button>
          </div>
        )}
      </div>

      <input
        ref={inputRef}
        type="file"
        accept="image/jpeg,image/png,image/webp,image/gif"
        className="sr-only"
        onChange={(e) => {
          const file = e.target.files?.[0];
          if (file) handleFile(file);
          e.target.value = "";
        }}
      />
    </div>
  );
}
