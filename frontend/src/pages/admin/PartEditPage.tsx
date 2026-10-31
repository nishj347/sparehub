import React, { useEffect, useState } from 'react';
import { Link, useNavigate, useParams } from 'react-router-dom';
import { ArrowLeft } from 'lucide-react';
import { adminPartsApi } from '../../api/adminParts';
import { ApiError } from '../../api/client';
import { PartCreatePayload, PartDetail, PartUpdatePayload } from '../../types/parts';
import { ErrorState } from '../../components/ui/ErrorState';
import { LoadingState } from '../../components/ui/LoadingState';
import { useToast } from '../../components/ui/Toast';
import { PartForm } from '../../components/admin/parts/PartForm';

export const PartEditPage: React.FC = () => {
  const { id } = useParams<{ id: string }>();
  const navigate = useNavigate();
  const { success, error: toastError } = useToast();

  const [part, setPart] = useState<PartDetail | null>(null);
  const [isLoading, setIsLoading] = useState(true);
  const [fetchError, setFetchError] = useState<string | null>(null);
  const [isSubmitting, setIsSubmitting] = useState(false);

  const partId = Number(id);

  const fetchPart = async () => {
    if (!partId || isNaN(partId)) {
      setFetchError('Invalid spare part identifier.');
      setIsLoading(false);
      return;
    }

    setIsLoading(true);
    setFetchError(null);
    try {
      const data = await adminPartsApi.getById(partId);
      setPart(data);
    } catch (err) {
      const msg = err instanceof ApiError ? err.message : 'Failed to retrieve spare part details.';
      setFetchError(msg);
    } finally {
      setIsLoading(false);
    }
  };

  useEffect(() => {
    fetchPart();
  }, [id]);

  const handleUpdate = async (
    payload: PartCreatePayload | PartUpdatePayload,
    imageFile: File | null,
    shouldRemoveImage: boolean
  ) => {
    if (!part) return;

    setIsSubmitting(true);
    try {
      // 1. Update basic details, specifications, and machines
      await adminPartsApi.update(part.id, payload as PartUpdatePayload);

      // 2. Image mutation
      if (shouldRemoveImage) {
        try {
          await adminPartsApi.deleteImage(part.id);
        } catch (imgErr) {
          toastError('Part updated, but failed to delete photo.');
        }
      } else if (imageFile) {
        try {
          await adminPartsApi.uploadImage(part.id, imageFile);
        } catch (imgErr) {
          toastError('Part updated, but failed to upload new photo.');
        }
      }

      success(`Spare part "${part.part_number}" updated successfully.`);
      navigate(`/admin/parts/${part.id}`);
    } finally {
      setIsSubmitting(false);
    }
  };

  if (isLoading) {
    return <LoadingState />;
  }

  if (fetchError || !part) {
    return (
      <div className="max-w-4xl mx-auto space-y-6">
        <Link
          to="/admin/parts"
          className="inline-flex items-center gap-1.5 text-xs font-medium text-slate-500 hover:text-slate-900 transition-colors"
        >
          <ArrowLeft className="w-3.5 h-3.5" />
          <span>Back to Parts Catalog</span>
        </Link>
        <ErrorState
          message={fetchError || 'Spare part not found.'}
          onRetry={fetchPart}
        />
      </div>
    );
  }

  return (
    <div className="max-w-4xl mx-auto space-y-6">
      {/* Header & Back Link */}
      <div className="space-y-1">
        <Link
          to={`/admin/parts/${part.id}`}
          className="inline-flex items-center gap-1.5 text-xs font-medium text-slate-500 hover:text-slate-900 transition-colors"
        >
          <ArrowLeft className="w-3.5 h-3.5" />
          <span>Back to {part.part_number} Detail</span>
        </Link>
        <h1 className="text-2xl font-bold tracking-tight text-slate-900">
          Edit Spare Part — <span className="font-mono text-primary-700">{part.part_number}</span>
        </h1>
        <p className="text-sm text-slate-500">
          Update specifications, brand, machinery associations, and part photo.
        </p>
      </div>

      {/* Main Form */}
      <PartForm
        initialData={part}
        isEdit={true}
        onSubmit={handleUpdate}
        isSubmitting={isSubmitting}
      />
    </div>
  );
};

