import React, { useEffect, useState, useCallback } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import {
  ArrowLeft,
  Copy,
  Check,
  Package,
  MapPin,
  RefreshCw,
  Cpu,
  AlertCircle,
} from 'lucide-react';
import { getPart } from '../../api/parts';
import { EmployeePartDetail, LocationStockDetail } from '../../types/partDetail';
import { IssueResponse } from '../../types/issues';
import { AvailabilityBadge } from '../../components/parts/AvailabilityBadge';
import { PartImage } from '../../components/parts/PartImage';
import { IssuePartModal } from '../../components/parts/IssuePartModal';
import { useToast } from '../../components/ui/Toast';
import { useAuth } from '../../auth/AuthContext';
import { ApiError } from '../../api/client';


function StorageField({ label, value }: { label: string; value: string | null }) {
  if (!value) return null;
  return (
    <div className="flex flex-col gap-0.5">
      <span className="text-[10px] font-semibold uppercase tracking-wider text-slate-400">{label}</span>
      <span className="text-sm font-medium text-slate-700">{value}</span>
    </div>
  );
}

// ─── Availability status label for table ────────────────────────────────────
const STATUS_LABEL: Record<string, { label: string; cls: string }> = {
  IN_STOCK: { label: 'In Stock', cls: 'bg-emerald-50 text-emerald-700 border border-emerald-200' },
  LOW_STOCK: { label: 'Low Stock', cls: 'bg-amber-50 text-amber-700 border border-amber-200' },
  OUT_OF_STOCK: { label: 'Out of Stock', cls: 'bg-rose-50 text-rose-600 border border-rose-200' },
};

function StatusChip({ status }: { status: string }) {
  const cfg = STATUS_LABEL[status] ?? STATUS_LABEL.OUT_OF_STOCK;
  return (
    <span className={`inline-flex items-center px-2 py-0.5 rounded text-[11px] font-medium ${cfg.cls}`}>
      {cfg.label}
    </span>
  );
}

// ═══════════════════════════════════════════════════════════════════════════
export const PartDetailPage: React.FC = () => {
  const { id } = useParams<{ id: string }>();
  const navigate = useNavigate();
  const { showToast } = useToast();
  const { user } = useAuth();

  const [part, setPart] = useState<EmployeePartDetail | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [is404, setIs404] = useState(false);
  const [copied, setCopied] = useState(false);

  // Issue Part modal state
  const [isIssueModalOpen, setIsIssueModalOpen] = useState(false);
  const [selectedIssueLocation, setSelectedIssueLocation] = useState<LocationStockDetail | null>(null);

  const handleOpenIssueModal = (locationRow: LocationStockDetail) => {
    setSelectedIssueLocation(locationRow);
    setIsIssueModalOpen(true);
  };

  const handleCloseIssueModal = () => {
    setIsIssueModalOpen(false);
    setSelectedIssueLocation(null);
  };

  const handleIssueSuccess = (res: IssueResponse) => {
    showToast(`${res.quantity_issued} unit(s) issued successfully.`, 'success');
    fetchPart();
  };

  const fetchPart = useCallback(async () => {
    if (!id || isNaN(Number(id))) {
      setIs404(true);
      setLoading(false);
      return;
    }

    setLoading(true);
    setError(null);
    setIs404(false);

    try {
      const data = await getPart(Number(id));
      setPart(data);
    } catch (err: unknown) {
      if (err instanceof ApiError) {
        if (err.status === 404 || err.status === 422) {
          setIs404(true);
        } else {
          setError(err.message || 'Failed to load spare part details.');
        }
      } else {
        setError('Network error or server unreachable. Please try again.');
      }
    } finally {
      setLoading(false);
    }
  }, [id]);

  useEffect(() => {
    fetchPart();
  }, [fetchPart]);

  const handleCopyPartNumber = () => {
    if (!part) return;
    navigator.clipboard.writeText(part.part_number);
    setCopied(true);
    showToast('Part ID copied', 'info');
    setTimeout(() => setCopied(false), 2000);
  };

  const handleBack = () => {
    if (window.history.length > 2) {
      navigate(-1);
    } else {
      navigate('/parts');
    }
  };

  // Loading skeleton
  if (loading) {
    return (
      <div className="space-y-6 animate-pulse" aria-busy="true">
        <div className="h-4 bg-slate-200 rounded w-24" />
        <div className="flex flex-col sm:flex-row justify-between gap-4">
          <div className="space-y-2">
            <div className="h-8 bg-slate-200 rounded w-64" />
            <div className="h-4 bg-slate-200 rounded w-40" />
          </div>
          <div className="h-8 bg-slate-200 rounded w-28" />
        </div>
        <div className="h-40 bg-slate-200 rounded-lg" />
        <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
          <div className="lg:col-span-2 space-y-6">
            <div className="h-72 bg-slate-200 rounded-lg" />
            <div className="h-32 bg-slate-200 rounded-lg" />
          </div>
          <div className="space-y-6">
            <div className="h-44 bg-slate-200 rounded-lg" />
          </div>
        </div>
      </div>
    );
  }

  if (is404) {
    return (
      <div className="flex flex-col items-center justify-center py-24 text-center gap-4">
        <div className="w-12 h-12 rounded-full bg-slate-100 flex items-center justify-center text-slate-400">
          <Package className="w-6 h-6" />
        </div>
        <h1 className="text-xl font-bold text-slate-800">Part not found or no longer available</h1>
        <p className="text-sm text-slate-500 max-w-md">
          The requested spare part could not be found or has been deactivated in the system.
        </p>
        <button
          type="button"
          onClick={handleBack}
          className="mt-2 inline-flex items-center gap-2 text-sm font-medium text-blue-600 hover:text-blue-800 focus:outline-none focus:ring-2 focus:ring-blue-500 rounded"
        >
          <ArrowLeft className="w-4 h-4" />
          Back to Spare Parts
        </button>
      </div>
    );
  }

  if (error || !part) {
    return (
      <div className="flex flex-col items-center justify-center py-20 text-center gap-4">
        <div className="w-12 h-12 rounded-full bg-rose-50 flex items-center justify-center text-rose-500">
          <AlertCircle className="w-6 h-6" />
        </div>
        <h1 className="text-lg font-semibold text-slate-800">Error loading part</h1>
        <p className="text-sm text-slate-500 max-w-md">{error}</p>
        <button
          type="button"
          onClick={fetchPart}
          className="inline-flex items-center gap-2 px-4 py-2 text-sm font-medium rounded bg-blue-600 text-white hover:bg-blue-700 transition-colors shadow-sm"
        >
          <RefreshCw className="w-4 h-4" />
          Retry
        </button>
      </div>
    );
  }

  // Separate the user's location row and other locations
  const myLocationRow = part.locations.find((l) => l.is_my_location);
  const otherLocations = part.locations.filter((l) => !l.is_my_location);
  const bestOtherLocation = [...otherLocations]
    .filter((l) => l.quantity > 0)
    .sort((a, b) => b.quantity - a.quantity)[0];

  // Primary display row: prefer user's location; fallback to best other
  const primaryDisplay = myLocationRow ?? bestOtherLocation ?? null;

  return (
    <div className="space-y-6">
      {/* Back button */}
      <div>
        <button
          type="button"
          onClick={handleBack}
          className="inline-flex items-center gap-2 text-sm font-medium text-slate-600 hover:text-slate-900 focus:outline-none focus:ring-2 focus:ring-blue-500 rounded transition-colors"
        >
          <ArrowLeft className="w-4 h-4" />
          Back to results
        </button>
      </div>

      {/* Part Header */}
      <div className="flex flex-col md:flex-row md:items-start justify-between gap-4 pb-5 border-b border-slate-200">
        <div className="space-y-1 min-w-0">
          <div className="flex items-center gap-3 flex-wrap">
            <h1 className="text-2xl font-bold tracking-tight text-slate-900">{part.name}</h1>
            <AvailabilityBadge status={part.availability_status} />
          </div>
          <div className="flex items-center gap-2 text-sm text-slate-500 flex-wrap">
            <span className="font-mono bg-slate-100 text-slate-800 px-2 py-0.5 rounded text-xs font-semibold tracking-wide flex items-center gap-1.5 border border-slate-200">
              {part.part_number}
              <button
                type="button"
                onClick={handleCopyPartNumber}
                aria-label="Copy Part ID"
                className="text-slate-400 hover:text-slate-700 focus:outline-none"
                title="Copy Part ID"
              >
                {copied ? <Check className="w-3.5 h-3.5 text-emerald-600" /> : <Copy className="w-3.5 h-3.5" />}
              </button>
            </span>
            <span className="text-slate-300">•</span>
            <span>{part.category}</span>
            {part.manufacturer && (
              <>
                <span className="text-slate-300">•</span>
                <span className="text-slate-400">Mfr: {part.manufacturer}</span>
              </>
            )}
          </div>
        </div>

        {/* Total inventory callout */}
        <div className="bg-slate-50 border border-slate-200 rounded px-4 py-3 shrink-0 text-right">
          <div className="text-[10px] text-slate-400 uppercase font-semibold tracking-wider">Total Inventory</div>
          <div className="text-xl font-bold text-slate-900 mt-0.5">
            {part.total_quantity}{' '}
            <span className="text-xs font-normal text-slate-500">units across all locations</span>
          </div>
        </div>
      </div>

      {/* ═══ AVAILABILITY & LOCATION — full-width prominent section ═══ */}
      <section className="bg-white border border-slate-200 rounded-lg overflow-hidden">
        <div className="px-5 py-3 border-b border-slate-100 bg-slate-50 flex items-center gap-2">
          <MapPin className="w-4 h-4 text-blue-600 shrink-0" />
          <h2 className="text-sm font-semibold text-slate-800">Availability &amp; Location</h2>
        </div>

        <div className="p-5 space-y-5">
          {/* Primary / your-location panel */}
          {primaryDisplay ? (
            <div
              className={`rounded border p-4 ${
                primaryDisplay.is_my_location
                  ? 'border-blue-200 bg-blue-50/50'
                  : 'border-slate-200 bg-slate-50'
              }`}
            >
              {/* Label */}
              <div className="text-[10px] font-semibold uppercase tracking-wider mb-2 text-slate-500">
                {primaryDisplay.is_my_location ? 'Your Location' : 'Primary Location'}
              </div>

              <div className="flex flex-col sm:flex-row sm:items-start sm:justify-between gap-4">
                {/* Left: plant + storage */}
                <div className="space-y-2">
                  <div className="text-base font-semibold text-slate-800">
                    {primaryDisplay.location.name}
                    {primaryDisplay.location.city
                      ? ` — ${primaryDisplay.location.city}`
                      : ''}
                  </div>
                  <div className="text-xl font-bold text-slate-900">
                    {primaryDisplay.quantity}{' '}
                    <span className="text-sm font-normal text-slate-500">units available</span>
                  </div>
                  <StatusChip status={primaryDisplay.availability_status} />

                  {/* Storage path */}
                  <div className="pt-2 border-t border-slate-200 grid grid-cols-1 sm:grid-cols-3 gap-3 mt-2">
                    <StorageField label="Store" value={primaryDisplay.store_name} />
                    <StorageField label="Rack" value={primaryDisplay.rack} />
                    <StorageField label="Bin" value={primaryDisplay.bin} />
                    {!primaryDisplay.store_name && !primaryDisplay.rack && !primaryDisplay.bin && (
                      <p className="text-xs text-slate-400 italic col-span-3">Storage details not recorded</p>
                    )}
                  </div>
                </div>

                {/* Right: Issue action */}
                <div className="sm:shrink-0 sm:pl-4 sm:border-l sm:border-slate-200">
                  {primaryDisplay.quantity > 0 ? (
                    <button
                      type="button"
                      onClick={() => handleOpenIssueModal(primaryDisplay)}
                      className="w-full sm:w-auto whitespace-nowrap py-2.5 px-5 bg-blue-600 hover:bg-blue-700 text-white font-semibold text-sm rounded transition-colors focus:outline-none focus:ring-2 focus:ring-blue-500 flex items-center justify-center gap-2"
                    >
                      <Package className="w-4 h-4" />
                      {primaryDisplay.is_my_location ? 'Issue Part' : `Issue from ${primaryDisplay.location.name}`}
                    </button>
                  ) : (
                    <button
                      type="button"
                      disabled
                      className="w-full sm:w-auto whitespace-nowrap py-2.5 px-5 bg-slate-100 text-slate-400 font-medium text-sm rounded border border-slate-200 cursor-not-allowed"
                    >
                      Out of Stock
                    </button>
                  )}
                  {!primaryDisplay.is_my_location && primaryDisplay.quantity > 0 && (
                    <p className="text-xs text-amber-700 text-center mt-1.5">
                      Not available at your location
                    </p>
                  )}
                </div>
              </div>
            </div>
          ) : (
            <div className="rounded border border-rose-200 bg-rose-50 p-4 text-sm text-rose-700 font-medium flex items-center gap-2">
              <AlertCircle className="w-4 h-4 shrink-0" />
              Out of stock at all locations
            </div>
          )}

          {/* Other locations table */}
          {part.locations.length > 1 && (
            <div>
              <h3 className="text-xs font-semibold text-slate-500 uppercase tracking-wider mb-2">
                All Locations ({part.locations.length})
              </h3>
              <div className="overflow-x-auto rounded border border-slate-200">
                <table className="w-full text-left text-xs border-collapse">
                  <thead>
                    <tr className="bg-slate-50 border-b border-slate-200 text-slate-500">
                      <th className="py-2 px-3 font-semibold">Location</th>
                      <th className="py-2 px-3 font-semibold text-right">Qty</th>
                      <th className="py-2 px-3 font-semibold">Store</th>
                      <th className="py-2 px-3 font-semibold">Rack</th>
                      <th className="py-2 px-3 font-semibold">Bin</th>
                      <th className="py-2 px-3 font-semibold">Status</th>
                      <th className="py-2 px-3 font-semibold text-right">Action</th>
                    </tr>
                  </thead>
                  <tbody>
                    {part.locations.map((loc) => (
                      <tr
                        key={loc.location.id}
                        className={`border-b border-slate-100 last:border-none ${
                          loc.is_my_location ? 'bg-blue-50/40' : ''
                        }`}
                      >
                        <td className="py-2 px-3 font-medium text-slate-800">
                          {loc.location.name}
                          {loc.is_my_location && (
                            <span className="ml-1.5 text-[10px] font-semibold text-blue-600 bg-blue-100 px-1.5 py-0.5 rounded">
                              Yours
                            </span>
                          )}
                        </td>
                        <td className="py-2 px-3 text-right font-semibold text-slate-800">
                          {loc.quantity}
                        </td>
                        <td className="py-2 px-3 text-slate-500">{loc.store_name || <span className="text-slate-300">—</span>}</td>
                        <td className="py-2 px-3 text-slate-500">{loc.rack || <span className="text-slate-300">—</span>}</td>
                        <td className="py-2 px-3 text-slate-500">{loc.bin || <span className="text-slate-300">—</span>}</td>
                        <td className="py-2 px-3">
                          <StatusChip status={loc.availability_status} />
                        </td>
                        <td className="py-2 px-3 text-right">
                          {loc.quantity > 0 ? (
                            <button
                              type="button"
                              onClick={() => handleOpenIssueModal(loc)}
                              className="px-2.5 py-1 text-[11px] font-semibold text-blue-700 bg-blue-50 hover:bg-blue-100 border border-blue-200 rounded transition-colors focus:outline-none focus:ring-2 focus:ring-blue-500"
                            >
                              Issue
                            </button>
                          ) : (
                            <span className="text-[11px] text-slate-400 italic">Out of stock</span>
                          )}
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            </div>
          )}
        </div>
      </section>

      {/* Main Grid: image + details */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        {/* Left Column (2 cols): Image, Description, Specifications */}
        <div className="lg:col-span-2 space-y-6">
          {/* Part Image */}
          <div className="bg-white rounded-lg border border-slate-200 overflow-hidden">
            <div className="h-72 sm:h-80 w-full flex items-center justify-center bg-slate-50">
              <PartImage
                src={part.image_url}
                alt={part.name}
                className="w-full h-full object-contain"
              />
            </div>
          </div>

          {/* Description */}
          {part.description && (
            <div className="bg-white rounded-lg border border-slate-200 p-6 space-y-2">
              <h2 className="text-xs font-semibold text-slate-500 uppercase tracking-wider">Description</h2>
              <p className="text-sm text-slate-600 whitespace-pre-line leading-relaxed">
                {part.description}
              </p>
            </div>
          )}

          {/* Technical Specifications */}
          {part.specifications && part.specifications.length > 0 && (
            <div className="bg-white rounded-lg border border-slate-200 p-6 space-y-3">
              <h2 className="text-xs font-semibold text-slate-500 uppercase tracking-wider">
                Specifications
              </h2>
              <div className="overflow-x-auto">
                <table className="w-full text-left text-sm border-collapse">
                  <tbody>
                    {part.specifications.map((spec, idx) => (
                      <tr
                        key={spec.key + idx}
                        className="border-b border-slate-100 last:border-none"
                      >
                        <td className="py-2 pr-4 font-medium text-slate-500 w-1/3">
                          {spec.key}
                        </td>
                        <td className="py-2 text-slate-800 font-mono text-xs">
                          {spec.value}
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            </div>
          )}
        </div>

        {/* Right Column (1 col): Machines */}
        <div className="space-y-6">
          {/* Machines Used In */}
          <div className="bg-white rounded-lg border border-slate-200 p-5 space-y-3">
            <div className="flex items-center gap-2">
              <Cpu className="w-4 h-4 text-slate-400" />
              <h2 className="text-xs font-semibold text-slate-500 uppercase tracking-wider">
                Used In Machines ({part.machines.length})
              </h2>
            </div>
            {part.machines.length > 0 ? (
              <div className="space-y-2">
                {part.machines.map((m) => (
                  <div
                    key={m.id}
                    className="p-3 bg-slate-50 rounded border border-slate-100 text-xs flex flex-col gap-0.5"
                  >
                    <div className="font-semibold text-slate-800">{m.name}</div>
                    <div className="font-mono text-slate-400">{m.code}</div>
                    {m.location_name && (
                      <div className="text-slate-400 text-[11px] flex items-center gap-1 mt-0.5">
                        <MapPin className="w-3 h-3" />
                        <span>{m.location_name}</span>
                      </div>
                    )}
                  </div>
                ))}
              </div>
            ) : (
              <p className="text-xs text-slate-400 italic">No active machinery mapped to this spare part.</p>
            )}
          </div>
        </div>
      </div>

      {/* Issue Part Modal */}
      {isIssueModalOpen && selectedIssueLocation && part && user && (
        <IssuePartModal
          isOpen={isIssueModalOpen}
          onClose={handleCloseIssueModal}
          part={part}
          selectedLocation={selectedIssueLocation}
          currentUser={user}
          onSuccess={handleIssueSuccess}
          onStockChange={fetchPart}
        />
      )}
    </div>
  );
};
