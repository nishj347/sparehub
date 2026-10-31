import React, { useEffect, useState } from 'react';
import { Link, useParams } from 'react-router-dom';
import {
  ArrowLeft,
  Edit2,
  Package,
  Plus,
  Power,
  Sliders,
  Warehouse,
} from 'lucide-react';
import { adminPartsApi } from '../../api/adminParts';
import { ApiError } from '../../api/client';
import { InventoryItemDetail, PartDetail } from '../../types/parts';
import { getAssetUrl } from '../../lib/assetUrl';
import { ConfirmDialog } from '../../components/ui/ConfirmDialog';
import { ErrorState } from '../../components/ui/ErrorState';
import { LoadingState } from '../../components/ui/LoadingState';
import { StatusBadge } from '../../components/ui/StatusBadge';
import { useToast } from '../../components/ui/Toast';
import { AdjustStockModal } from '../../components/admin/parts/AdjustStockModal';
import { InventoryLocationModal } from '../../components/admin/parts/InventoryLocationModal';
import { ReceiveStockModal } from '../../components/admin/parts/ReceiveStockModal';
import { StockStatusBadge } from '../../components/admin/parts/StockStatusBadge';

export const PartDetailPage: React.FC = () => {
  const { id } = useParams<{ id: string }>();
  const { success, error: toastError } = useToast();

  const [part, setPart] = useState<PartDetail | null>(null);
  const [isLoading, setIsLoading] = useState(true);
  const [fetchError, setFetchError] = useState<string | null>(null);

  // Status toggle confirmation
  const [isConfirmStatusOpen, setIsConfirmStatusOpen] = useState(false);
  const [isTogglingStatus, setIsTogglingStatus] = useState(false);

  // Modals
  const [activeReceiveItem, setActiveReceiveItem] = useState<InventoryItemDetail | null>(null);
  const [activeAdjustItem, setActiveAdjustItem] = useState<InventoryItemDetail | null>(null);
  const [locationModalState, setLocationModalState] = useState<{
    isOpen: boolean;
    mode: 'add' | 'edit';
    item: InventoryItemDetail | null;
  }>({
    isOpen: false,
    mode: 'add',
    item: null,
  });

  const partId = Number(id);

  const fetchPartDetail = async () => {
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
    fetchPartDetail();
  }, [id]);

  const handleToggleStatus = async () => {
    if (!part) return;

    setIsTogglingStatus(true);
    try {
      if (part.is_active) {
        await adminPartsApi.deactivate(part.id);
        success(`Spare part "${part.part_number}" deactivated.`);
      } else {
        await adminPartsApi.activate(part.id);
        success(`Spare part "${part.part_number}" activated.`);
      }
      setIsConfirmStatusOpen(false);
      await fetchPartDetail();
    } catch (err) {
      const msg = err instanceof ApiError ? err.message : 'Failed to update status.';
      toastError(msg);
    } finally {
      setIsTogglingStatus(false);
    }
  };

  if (isLoading) {
    return <LoadingState />;
  }

  if (fetchError || !part) {
    return (
      <div className="max-w-6xl mx-auto space-y-6">
        <Link
          to="/admin/parts"
          className="inline-flex items-center gap-1.5 text-xs font-medium text-slate-500 hover:text-slate-900 transition-colors"
        >
          <ArrowLeft className="w-3.5 h-3.5" />
          <span>Back to Parts Catalog</span>
        </Link>
        <ErrorState
          message={fetchError || 'Spare part not found.'}
          onRetry={fetchPartDetail}
        />
      </div>
    );
  }

  const existingLocIds = part.inventory.map((inv) => inv.location.id);
  const imageUrl = getAssetUrl(part.image_url);

  return (
    <div className="max-w-6xl mx-auto space-y-6">
      {/* Top Breadcrumb & Action Bar */}
      <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4">
        <div className="space-y-1">
          <Link
            to="/admin/parts"
            className="inline-flex items-center gap-1.5 text-xs font-medium text-slate-500 hover:text-slate-900 transition-colors"
          >
            <ArrowLeft className="w-3.5 h-3.5" />
            <span>Back to Parts Catalog</span>
          </Link>
          <div className="flex flex-wrap items-center gap-3">
            <h1 className="text-2xl font-bold tracking-tight text-slate-900">
              {part.name}
            </h1>
            <span className="font-mono text-sm font-semibold bg-slate-100 text-slate-800 border border-slate-300 px-2.5 py-0.5 rounded">
              {part.part_number}
            </span>
            <StockStatusBadge
              lowStock={part.low_stock}
              outOfStock={part.out_of_stock}
            />
            <StatusBadge isActive={part.is_active} />
          </div>
        </div>

        {/* Action buttons */}
        <div className="flex items-center gap-2.5 shrink-0">
          <button
            type="button"
            onClick={() => setIsConfirmStatusOpen(true)}
            className={`inline-flex items-center gap-1.5 px-3 py-1.5 text-xs font-medium rounded-lg border transition-colors ${
              part.is_active
                ? 'text-rose-700 bg-rose-50 border-rose-200 hover:bg-rose-100'
                : 'text-emerald-700 bg-emerald-50 border-emerald-200 hover:bg-emerald-100'
            }`}
          >
            <Power className="w-3.5 h-3.5" />
            <span>{part.is_active ? 'Deactivate Part' : 'Activate Part'}</span>
          </button>

          <Link
            to={`/admin/parts/${part.id}/edit`}
            className="inline-flex items-center gap-1.5 px-3.5 py-1.5 text-xs font-medium text-white bg-blue-600 rounded-lg hover:bg-blue-700 shadow-sm transition-colors"
          >
            <Edit2 className="w-3.5 h-3.5" />
            <span>Edit Part</span>
          </Link>
        </div>
      </div>

      {/* Main Info Card */}
      <div className="bg-white border border-slate-200 rounded-xl p-6 shadow-sm">
        <div className="grid grid-cols-1 md:grid-cols-4 gap-6">
          {/* Photo */}
          <div className="md:col-span-1">
            <div className="w-full aspect-square rounded-xl border border-slate-200 bg-slate-50 flex items-center justify-center overflow-hidden shadow-sm">
              {imageUrl ? (
                <img
                  src={imageUrl}
                  alt={part.name}
                  className="w-full h-full object-cover"
                />
              ) : (
                <div className="flex flex-col items-center justify-center text-slate-400 p-4 text-center">
                  <Package className="w-12 h-12 stroke-[1.5] text-slate-300 mb-2" />
                  <span className="text-xs font-medium">No Photograph</span>
                </div>
              )}
            </div>
          </div>

          {/* Core Master Properties */}
          <div className="md:col-span-3 space-y-4">
            <div className="grid grid-cols-2 sm:grid-cols-4 gap-4 pb-4 border-b border-slate-100">
              <div>
                <span className="text-[11px] font-semibold uppercase tracking-wider text-slate-400 block">
                  Category
                </span>
                <span className="text-sm font-medium text-slate-900 mt-0.5 block">
                  {part.category}
                </span>
              </div>
              <div>
                <span className="text-[11px] font-semibold uppercase tracking-wider text-slate-400 block">
                  Manufacturer
                </span>
                <span className="text-sm font-medium text-slate-900 mt-0.5 block">
                  {part.manufacturer || '—'}
                </span>
              </div>
              <div>
                <span className="text-[11px] font-semibold uppercase tracking-wider text-slate-400 block">
                  Total Inventory
                </span>
                <span className="text-sm font-bold font-mono text-slate-900 mt-0.5 block">
                  {part.total_quantity.toLocaleString()} units
                </span>
              </div>
              <div>
                <span className="text-[11px] font-semibold uppercase tracking-wider text-slate-400 block">
                  Sites Stored
                </span>
                <span className="text-sm font-medium text-slate-900 mt-0.5 block">
                  {part.inventory.length} {part.inventory.length === 1 ? 'plant' : 'plants'}
                </span>
              </div>
            </div>

            {/* Description */}
            {part.description && (
              <div>
                <span className="text-[11px] font-semibold uppercase tracking-wider text-slate-400 block mb-1">
                  Description
                </span>
                <p className="text-sm text-slate-600 leading-relaxed">
                  {part.description}
                </p>
              </div>
            )}

            {/* Technical Specifications */}
            <div>
              <span className="text-[11px] font-semibold uppercase tracking-wider text-slate-400 block mb-2">
                Technical Specifications
              </span>
              {part.specifications && Object.keys(part.specifications).length > 0 ? (
                <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-2">
                  {Object.entries(part.specifications).map(([key, value]) => (
                    <div
                      key={key}
                      className="px-3 py-2 bg-slate-50 border border-slate-200 rounded-lg text-xs"
                    >
                      <span className="font-semibold text-slate-700 block truncate">
                        {key}
                      </span>
                      <span className="font-mono text-slate-900 truncate block">
                        {String(value)}
                      </span>
                    </div>
                  ))}
                </div>
              ) : (
                <p className="text-xs text-slate-400 italic">No technical specifications defined.</p>
              )}
            </div>

            {/* Machinery Compatibility */}
            <div>
              <span className="text-[11px] font-semibold uppercase tracking-wider text-slate-400 block mb-2">
                Compatible Machinery
              </span>
              {part.machines && part.machines.length > 0 ? (
                <div className="flex flex-wrap gap-2">
                  {part.machines.map((m) => (
                    <span
                      key={m.id}
                      className="inline-flex items-center gap-1.5 px-2.5 py-1 rounded-lg text-xs font-mono bg-slate-100 text-slate-800 border border-slate-200"
                    >
                      <span className="font-semibold">{m.name}</span>
                      <span className="text-slate-500">({m.code})</span>
                      {!m.is_active && (
                        <span className="text-[10px] bg-amber-100 text-amber-800 px-1 py-0.2 rounded font-sans font-medium">
                          Inactive Machine
                        </span>
                      )}
                    </span>
                  ))}
                </div>
              ) : (
                <p className="text-xs text-slate-400 italic">
                  Not linked to any specific machine models.
                </p>
              )}
            </div>
          </div>
        </div>
      </div>

      {/* Inventory by Location Section */}
      <div className="bg-white border border-slate-200 rounded-xl overflow-hidden shadow-sm">
        <div className="p-5 border-b border-slate-200 flex flex-col sm:flex-row sm:items-center justify-between gap-3 bg-slate-50/75">
          <div className="flex items-center gap-2.5">
            <Warehouse className="w-5 h-5 text-slate-600" />
            <div>
              <h2 className="text-base font-semibold text-slate-900">
                Inventory Across Plants & Sites
              </h2>
              <p className="text-xs text-slate-500">
                Independent stock balances and bin coordinates for each manufacturing location.
              </p>
            </div>
          </div>

          <button
            type="button"
            onClick={() =>
              setLocationModalState({
                isOpen: true,
                mode: 'add',
                item: null,
              })
            }
            className="inline-flex items-center gap-1.5 px-3 py-1.5 text-xs font-medium text-blue-600 bg-blue-50 border border-blue-200 rounded-lg hover:bg-blue-100 transition-colors shrink-0"
          >
            <Plus className="w-3.5 h-3.5" />
            <span>Add Plant Location</span>
          </button>
        </div>

        {part.inventory.length === 0 ? (
          <div className="p-8 text-center text-slate-500 space-y-3">
            <p className="text-sm">No storage locations assigned to this spare part yet.</p>
            <button
              type="button"
              onClick={() =>
                setLocationModalState({
                  isOpen: true,
                  mode: 'add',
                  item: null,
                })
              }
              className="px-4 py-2 text-xs font-medium text-white bg-blue-600 rounded-lg hover:bg-blue-700 transition-colors"
            >
              + Assign First Plant Location
            </button>
          </div>
        ) : (
          <div className="overflow-x-auto">
            <table className="w-full text-left border-collapse text-xs">
              <thead>
                <tr className="border-b border-slate-200 bg-slate-50/50 text-slate-500 uppercase tracking-wider font-semibold">
                  <th className="px-5 py-3">Plant / Location</th>
                  <th className="px-5 py-3">Store</th>
                  <th className="px-5 py-3">Rack & Bin</th>
                  <th className="px-5 py-3 text-right">On Hand</th>
                  <th className="px-5 py-3 text-right">Min Stock</th>
                  <th className="px-5 py-3 text-center">Stock Level</th>
                  <th className="px-5 py-3 text-right">Actions</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-100 text-slate-700">
                {part.inventory.map((item) => (
                  <tr key={item.id} className="hover:bg-slate-50/75 transition-colors">
                    <td className="px-5 py-3 font-medium text-slate-900">
                      <div>{item.location.name}</div>
                      <div className="text-[11px] text-slate-400 font-mono">
                        {item.location.code}
                      </div>
                    </td>
                    <td className="px-5 py-3 text-slate-600">
                      {item.store_name || <span className="text-slate-300">—</span>}
                    </td>
                    <td className="px-5 py-3 font-mono text-slate-600">
                      {item.rack || item.bin ? (
                        <span>
                          R: {item.rack || '—'} / B: {item.bin || '—'}
                        </span>
                      ) : (
                        <span className="text-slate-300">—</span>
                      )}
                    </td>
                    <td className="px-5 py-3 text-right font-mono font-bold text-sm text-slate-900">
                      {item.quantity.toLocaleString()}
                    </td>
                    <td className="px-5 py-3 text-right font-mono text-slate-500">
                      {item.min_stock_level}
                    </td>
                    <td className="px-5 py-3 text-center">
                      <StockStatusBadge
                        lowStock={item.low_stock}
                        outOfStock={item.out_of_stock}
                      />
                    </td>
                    <td className="px-5 py-3 text-right whitespace-nowrap">
                      <div className="flex items-center justify-end gap-1.5">
                        <button
                          type="button"
                          onClick={() => setActiveReceiveItem(item)}
                          disabled={!part.is_active}
                          title={
                            part.is_active
                              ? 'Receive incoming stock'
                              : 'Cannot receive stock on inactive part'
                          }
                          className="px-2.5 py-1 text-xs font-medium text-emerald-700 bg-emerald-50 border border-emerald-200 rounded hover:bg-emerald-100 disabled:opacity-40 disabled:cursor-not-allowed transition-colors"
                        >
                          Receive
                        </button>
                        <button
                          type="button"
                          onClick={() => setActiveAdjustItem(item)}
                          className="px-2.5 py-1 text-xs font-medium text-amber-700 bg-amber-50 border border-amber-200 rounded hover:bg-amber-100 transition-colors"
                          title="Record physical count adjustment"
                        >
                          Adjust
                        </button>
                        <button
                          type="button"
                          onClick={() =>
                            setLocationModalState({
                              isOpen: true,
                              mode: 'edit',
                              item,
                            })
                          }
                          className="p-1 text-slate-500 hover:text-slate-800 bg-slate-50 hover:bg-slate-100 border border-slate-200 rounded transition-colors"
                          title="Edit shelf coordinates"
                        >
                          <Sliders className="w-3.5 h-3.5" />
                        </button>
                      </div>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </div>

      {/* Recent Ledger Activity Card */}
      <div className="bg-white border border-slate-200 rounded-xl overflow-hidden shadow-sm">
        <div className="p-5 border-b border-slate-200 bg-slate-50/75">
          <h2 className="text-base font-semibold text-slate-900">
            Recent Ledger Activity (Last 10 Transactions)
          </h2>
          <p className="text-xs text-slate-500">
            Immutable audit trail of all receipts, issues, and inventory reconciliations for this part.
          </p>
        </div>

        {part.recent_transactions.length === 0 ? (
          <div className="p-8 text-center text-slate-400 text-xs italic">
            No transactions recorded yet for this spare part.
          </div>
        ) : (
          <div className="overflow-x-auto">
            <table className="w-full text-left border-collapse text-xs">
              <thead>
                <tr className="border-b border-slate-200 bg-slate-50/50 text-slate-500 uppercase tracking-wider font-semibold">
                  <th className="px-5 py-3">Timestamp</th>
                  <th className="px-5 py-3">Type</th>
                  <th className="px-5 py-3 text-right">Quantity Change</th>
                  <th className="px-5 py-3 text-right">Resulting Balance</th>
                  <th className="px-5 py-3">Location</th>
                  <th className="px-5 py-3">Performed By</th>
                  <th className="px-5 py-3">Notes / Ref</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-100 text-slate-700">
                {part.recent_transactions.map((tx) => {
                  const isPositive = tx.quantity_change > 0;
                  const isNegative = tx.quantity_change < 0;

                  return (
                    <tr key={tx.id} className="hover:bg-slate-50/75 transition-colors">
                      <td className="px-5 py-3 text-slate-500 whitespace-nowrap">
                        {new Date(tx.created_at).toLocaleString()}
                      </td>
                      <td className="px-5 py-3">
                        <span
                          className={`inline-flex items-center px-2 py-0.5 rounded text-[11px] font-semibold ${
                            tx.type === 'RECEIVED'
                              ? 'bg-emerald-50 text-emerald-700 border border-emerald-200'
                              : tx.type === 'ISSUED'
                              ? 'bg-blue-50 text-blue-700 border border-blue-200'
                              : 'bg-amber-50 text-amber-700 border border-amber-200'
                          }`}
                        >
                          {tx.type}
                        </span>
                      </td>
                      <td className="px-5 py-3 text-right font-mono font-semibold">
                        <span
                          className={
                            isPositive
                              ? 'text-emerald-600'
                              : isNegative
                              ? 'text-rose-600'
                              : 'text-slate-600'
                          }
                        >
                          {isPositive ? `+${tx.quantity_change}` : tx.quantity_change}
                        </span>
                      </td>
                      <td className="px-5 py-3 text-right font-mono text-slate-900 font-semibold">
                        {tx.quantity_after != null ? tx.quantity_after : '—'}
                      </td>
                      <td className="px-5 py-3 text-slate-600">
                        {tx.location?.name || `Location #${tx.location?.id}`}
                      </td>
                      <td className="px-5 py-3 text-slate-600">
                        {tx.user ? `${tx.user.name} (${tx.user.employee_id})` : 'System'}
                      </td>
                      <td className="px-5 py-3 text-slate-500 max-w-xs truncate" title={tx.notes || ''}>
                        {tx.notes || <span className="text-slate-300 italic">—</span>}
                      </td>
                    </tr>
                  );
                })}
              </tbody>
            </table>
          </div>
        )}

        <div className="p-3 bg-slate-50 border-t border-slate-100 text-[11px] text-slate-400 text-center">
          Full company-wide transaction ledger is available in Inventory Activity.
        </div>
      </div>

      {/* Modals */}
      {/* 1. Receive Stock Modal */}
      <ReceiveStockModal
        isOpen={Boolean(activeReceiveItem)}
        onClose={() => setActiveReceiveItem(null)}
        inventoryItem={activeReceiveItem}
        partIsActive={part.is_active}
        onSuccess={fetchPartDetail}
      />

      {/* 2. Adjust Stock Modal */}
      <AdjustStockModal
        isOpen={Boolean(activeAdjustItem)}
        onClose={() => setActiveAdjustItem(null)}
        inventoryItem={activeAdjustItem}
        onSuccess={fetchPartDetail}
      />

      {/* 3. Inventory Location Modal (Add / Edit) */}
      <InventoryLocationModal
        isOpen={locationModalState.isOpen}
        onClose={() =>
          setLocationModalState({
            isOpen: false,
            mode: 'add',
            item: null,
          })
        }
        mode={locationModalState.mode}
        partId={part.id}
        inventoryItem={locationModalState.item}
        existingLocationIds={existingLocIds}
        onSuccess={fetchPartDetail}
      />

      {/* 4. Deactivate / Activate Part Confirmation */}
      <ConfirmDialog
        isOpen={isConfirmStatusOpen}
        onClose={() => setIsConfirmStatusOpen(false)}
        onConfirm={handleToggleStatus}
        title={part.is_active ? 'Deactivate Spare Part' : 'Activate Spare Part'}
        message={
          part.is_active ? (
            <div className="space-y-2">
              <p>
                Are you sure you want to deactivate{' '}
                <strong className="text-slate-900">{part.part_number}</strong> (
                {part.name})?
              </p>
              <p className="text-xs text-amber-700 bg-amber-50 p-2.5 rounded-lg border border-amber-200">
                Deactivated parts cannot be issued by employees or received into inventory. Existing stock balances and transaction ledger records remain intact.
              </p>
            </div>
          ) : (
            <p>
              Activate <strong className="text-slate-900">{part.part_number}</strong> (
              {part.name})? This will allow plant staff to issue and receive stock once again.
            </p>
          )
        }
        confirmText={part.is_active ? 'Deactivate' : 'Activate'}
        isDestructive={part.is_active}
        isLoading={isTogglingStatus}
      />
    </div>
  );
};
