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
  Boxes,
  AlertCircle,
} from 'lucide-react';
import { getPart } from '../../api/parts';
import { EmployeePartDetail } from '../../types/partDetail';
import { AvailabilityBadge } from '../../components/parts/AvailabilityBadge';
import { PartImage } from '../../components/parts/PartImage';
import { LocationLine } from '../../components/parts/LocationLine';
import { useToast } from '../../components/ui/Toast';
import { ApiError } from '../../api/client';

export const PartDetailPage: React.FC = () => {
  const { id } = useParams<{ id: string }>();
  const navigate = useNavigate();
  const { showToast } = useToast();

  const [part, setPart] = useState<EmployeePartDetail | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [is404, setIs404] = useState(false);
  const [copied, setCopied] = useState(false);

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
        <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
          <div className="lg:col-span-2 space-y-6">
            <div className="h-72 bg-slate-200 rounded-lg" />
            <div className="h-32 bg-slate-200 rounded-lg" />
          </div>
          <div className="space-y-6">
            <div className="h-44 bg-slate-200 rounded-lg" />
            <div className="h-64 bg-slate-200 rounded-lg" />
          </div>
        </div>
      </div>
    );
  }

  // Not found state (404, 422 or invalid id)
  if (is404) {
    return (
      <div className="flex flex-col items-center justify-center py-24 text-center gap-4">
        <div className="w-12 h-12 rounded-full bg-slate-100 flex items-center justify-center text-slate-400">
          <Package className="w-6 h-6" />
        </div>
        <h1 className="text-xl font-bold text-slate-800">
          Part not found or no longer available
        </h1>
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

  // Error state
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

  // Separate caller's location row and other locations
  const myLocationRow = part.locations.find((l) => l.is_my_location);
  const otherLocations = part.locations.filter((l) => !l.is_my_location);

  // Highest stock other location (fallback recommendation)
  const bestOtherLocation = [...otherLocations]
    .filter((l) => l.quantity > 0)
    .sort((a, b) => b.quantity - a.quantity)[0];

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
      <div className="flex flex-col md:flex-row md:items-start justify-between gap-4 pb-6 border-b border-slate-200">
        <div className="space-y-1">
          <div className="flex items-center gap-3 flex-wrap">
            <h1 className="text-2xl font-bold tracking-tight text-slate-900">
              {part.name}
            </h1>
            <AvailabilityBadge status={part.availability_status} />
          </div>

          <div className="flex items-center gap-2 text-sm text-slate-600 flex-wrap">
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
                <span className="text-slate-500">Mfr: {part.manufacturer}</span>
              </>
            )}
          </div>
        </div>

        {/* Global Total Quantity Callout */}
        <div className="bg-slate-50 border border-slate-200 rounded-lg p-3 shrink-0 text-right">
          <div className="text-xs text-slate-500 uppercase font-semibold tracking-wider">
            Total Inventory
          </div>
          <div className="text-xl font-bold text-slate-900 mt-0.5">
            {part.total_quantity} <span className="text-xs font-normal text-slate-500">units across all locations</span>
          </div>
        </div>
      </div>

      {/* Main Grid: 2 columns on desktop, stacked on mobile */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        {/* Left Column (2 cols): Image, Description, Specifications */}
        <div className="lg:col-span-2 space-y-6">
          {/* Part Image */}
          <div className="bg-white rounded-lg border border-slate-200 overflow-hidden shadow-sm">
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
            <div className="bg-white rounded-lg border border-slate-200 p-6 shadow-sm space-y-2">
              <h2 className="text-sm font-semibold text-slate-800 uppercase tracking-wider">
                Description
              </h2>
              <p className="text-sm text-slate-600 whitespace-pre-line leading-relaxed">
                {part.description}
              </p>
            </div>
          )}

          {/* Technical Specifications */}
          {part.specifications && part.specifications.length > 0 && (
            <div className="bg-white rounded-lg border border-slate-200 p-6 shadow-sm space-y-3">
              <h2 className="text-sm font-semibold text-slate-800 uppercase tracking-wider">
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

          {/* Machines Used In */}
          <div className="bg-white rounded-lg border border-slate-200 p-6 shadow-sm space-y-3">
            <div className="flex items-center gap-2">
              <Cpu className="w-4 h-4 text-slate-500" />
              <h2 className="text-sm font-semibold text-slate-800 uppercase tracking-wider">
                Used In Machines ({part.machines.length})
              </h2>
            </div>
            {part.machines.length > 0 ? (
              <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
                {part.machines.map((m) => (
                  <div
                    key={m.id}
                    className="p-3 bg-slate-50 rounded border border-slate-200 text-xs flex flex-col justify-between"
                  >
                    <div>
                      <div className="font-semibold text-slate-800">{m.name}</div>
                      <div className="font-mono text-slate-500 mt-0.5">Code: {m.code}</div>
                    </div>
                    {m.location_name && (
                      <div className="text-slate-400 text-[11px] mt-2 flex items-center gap-1">
                        <MapPin className="w-3 h-3" />
                        <span>{m.location_name}</span>
                      </div>
                    )}
                  </div>
                ))}
              </div>
            ) : (
              <p className="text-xs text-slate-500 italic">
                No active machinery mapped to this spare part.
              </p>
            )}
          </div>
        </div>

        {/* Right Column (1 col): Availability, Location, Actions */}
        <div className="space-y-6">
          {/* Action Card */}
          <div className="bg-white rounded-lg border border-slate-200 p-6 shadow-sm space-y-3">
            <h2 className="text-sm font-semibold text-slate-800">Part Actions</h2>
            <button
              type="button"
              disabled
              className="w-full py-2.5 px-4 bg-slate-100 text-slate-400 font-medium text-sm rounded-lg border border-slate-200 cursor-not-allowed transition-colors"
            >
              Issue Part
            </button>
            <p className="text-xs text-slate-500 text-center">
              Issuing parts will be available in the next module.
            </p>
          </div>

          {/* Your Location Availability Card */}
          <div className="bg-white rounded-lg border border-blue-200 shadow-sm overflow-hidden">
            <div className="bg-blue-50/70 px-4 py-3 border-b border-blue-100 flex items-center justify-between">
              <span className="text-xs font-semibold text-blue-900 uppercase tracking-wider flex items-center gap-1.5">
                <MapPin className="w-3.5 h-3.5 text-blue-600" />
                Your Plant Location
              </span>
              {myLocationRow && (
                <span className="text-xs font-medium text-blue-800">
                  {myLocationRow.location.name}
                </span>
              )}
            </div>

            <div className="p-4 space-y-3">
              {myLocationRow && myLocationRow.quantity > 0 ? (
                <>
                  <div>
                    <div className="text-2xl font-bold text-slate-900">
                      {myLocationRow.quantity}{' '}
                      <span className="text-sm font-normal text-slate-500">units available</span>
                    </div>
                    <div className="mt-1">
                      <AvailabilityBadge status={myLocationRow.availability_status} />
                    </div>
                  </div>

                  <div className="pt-2 border-t border-slate-100">
                    <div className="text-xs font-medium text-slate-500 mb-1">
                      Storage Coordinates:
                    </div>
                    <LocationLine
                      primary={{
                        location: {
                          id: myLocationRow.location.id,
                          name: myLocationRow.location.name,
                          code: myLocationRow.location.code,
                        },
                        quantity: myLocationRow.quantity,
                        store_name: myLocationRow.store_name,
                        rack: myLocationRow.rack,
                        bin: myLocationRow.bin,
                        is_my_location: true,
                      }}
                    />
                  </div>
                </>
              ) : (
                <div className="space-y-2">
                  <div className="text-sm font-medium text-rose-600 flex items-center gap-1.5">
                    <AlertCircle className="w-4 h-4 shrink-0" />
                    Not available at your location
                  </div>
                  {bestOtherLocation ? (
                    <p className="text-xs text-slate-600">
                      Stock is available at{' '}
                      <span className="font-semibold text-slate-800">
                        {bestOtherLocation.location.name} ({bestOtherLocation.quantity} units)
                      </span>.
                    </p>
                  ) : (
                    <p className="text-xs text-slate-500">
                      This item is currently out of stock at all locations.
                    </p>
                  )}
                </div>
              )}
            </div>
          </div>

          {/* Other Locations Stock Card */}
          <div className="bg-white rounded-lg border border-slate-200 shadow-sm p-4 space-y-3">
            <div className="flex items-center gap-1.5">
              <Boxes className="w-4 h-4 text-slate-500" />
              <h2 className="text-sm font-semibold text-slate-800 uppercase tracking-wider">
                Other Locations ({otherLocations.length})
              </h2>
            </div>

            {otherLocations.length > 0 ? (
              <div className="overflow-x-auto">
                <table className="w-full text-left text-xs border-collapse">
                  <thead>
                    <tr className="border-b border-slate-200 text-slate-500">
                      <th className="py-2 pr-2 font-medium">Location</th>
                      <th className="py-2 px-2 font-medium text-right">Qty</th>
                      <th className="py-2 pl-2 font-medium">Shelf Details</th>
                    </tr>
                  </thead>
                  <tbody>
                    {otherLocations.map((loc) => (
                      <tr
                        key={loc.location.id}
                        className="border-b border-slate-100 last:border-none"
                      >
                        <td className="py-2 pr-2 font-medium text-slate-800">
                          {loc.location.name}
                        </td>
                        <td className="py-2 px-2 text-right">
                          <span
                            className={`font-semibold ${
                              loc.quantity === 0 ? 'text-slate-400' : 'text-slate-900'
                            }`}
                          >
                            {loc.quantity}
                          </span>
                        </td>
                        <td className="py-2 pl-2 text-slate-500">
                          {loc.store_name || loc.rack || loc.bin ? (
                            <span>
                              {[loc.store_name, loc.rack ? `R:${loc.rack}` : null, loc.bin ? `B:${loc.bin}` : null]
                                .filter(Boolean)
                                .join(' / ')}
                            </span>
                          ) : (
                            <span className="italic text-slate-400">—</span>
                          )}
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            ) : (
              <p className="text-xs text-slate-500 italic">
                No other plant locations assigned.
              </p>
            )}
          </div>
        </div>
      </div>
    </div>
  );
};
