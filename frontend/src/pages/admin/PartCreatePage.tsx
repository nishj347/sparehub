import React, { useState } from 'react';
import { Link, useNavigate } from 'react-router-dom';
import { ArrowLeft } from 'lucide-react';
import { adminPartsApi } from '../../api/adminParts';
import { PartCreatePayload, PartUpdatePayload } from '../../types/parts';
import { useToast } from '../../components/ui/Toast';
import { PartForm } from '../../components/admin/parts/PartForm';

export const PartCreatePage: React.FC = () => {
  const navigate = useNavigate();
  const { success, error: toastError } = useToast();
  const [isSubmitting, setIsSubmitting] = useState(false);

  const handleCreate = async (
    payload: PartCreatePayload | PartUpdatePayload,
    imageFile: File | null
  ) => {
    setIsSubmitting(true);
    try {
      const created = await adminPartsApi.create(payload as PartCreatePayload);

      // Handle image upload if a file was selected
      if (imageFile) {
        try {
          await adminPartsApi.uploadImage(created.id, imageFile);
        } catch (imgErr) {
          toastError(
            'Spare part created, but photo upload failed. You can retry uploading the image here.'
          );
          navigate(`/admin/parts/${created.id}/edit`);
          return;
        }
      }

      success(`Spare part "${created.part_number}" created successfully.`);
      navigate(`/admin/parts/${created.id}`);
    } finally {
      setIsSubmitting(false);
    }
  };

  return (
    <div className="max-w-4xl mx-auto space-y-6">
      {/* Header & Back Link */}
      <div className="space-y-1">
        <Link
          to="/admin/parts"
          className="inline-flex items-center gap-1.5 text-xs font-medium text-slate-500 hover:text-slate-900 transition-colors"
        >
          <ArrowLeft className="w-3.5 h-3.5" />
          <span>Back to Parts Catalog</span>
        </Link>
        <h1 className="text-2xl font-bold tracking-tight text-slate-900">
          New Spare Part
        </h1>
        <p className="text-sm text-slate-500">
          Register a new component in the central enterprise catalog.
        </p>
      </div>

      {/* Main Form */}
      <PartForm
        isEdit={false}
        onSubmit={handleCreate}
        isSubmitting={isSubmitting}
      />
    </div>
  );
};

