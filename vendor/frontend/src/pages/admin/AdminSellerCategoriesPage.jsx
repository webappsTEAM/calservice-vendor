import React, { useState, useEffect, useMemo, useCallback } from 'react';
import { Sidebar } from '../../components/common/Sidebar.jsx';
import { useAuth } from '../../context/AuthProvider.jsx';
import {
  apiGetSellerHubCategories,
  apiCreateSellerHubCategory,
  apiUpdateSellerHubCategory,
  apiDeleteSellerHubCategory,
} from '../../api/workforceService.js';
import {
  Store,
  Layers,
  Search,
  Plus,
  Edit2,
  Trash2,
  CheckCircle2,
  XCircle,
  AlertCircle,
  RefreshCw,
  X,
  ArrowUpDown,
  Package,
  ShoppingBag,
  Sparkles,
  Carrot,
  Wrench,
  Tag,
  ChevronRight,
  FolderTree,
  CornerDownRight,
  Folder,
  FolderOpen,
  Info,
  Maximize2,
  Minimize2,
} from 'lucide-react';

const AVAILABLE_ICONS = [
  { name: 'Store', icon: Store },
  { name: 'Package', icon: Package },
  { name: 'ShoppingBag', icon: ShoppingBag },
  { name: 'Carrot', icon: Carrot },
  { name: 'Sparkles', icon: Sparkles },
  { name: 'Wrench', icon: Wrench },
  { name: 'Tag', icon: Tag },
  { name: 'Layers', icon: Layers },
];

export function AdminSellerCategoriesPage() {
  const { user, isPlatformAdmin } = useAuth();
  const isSuperAdmin = isPlatformAdmin || user?.is_superuser;

  const [allCategories, setAllCategories] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [search, setSearch] = useState('');
  const [statusFilter, setStatusFilter] = useState('all'); // 'all', 'active', 'inactive'
  const [ordering, setOrdering] = useState('sort_order');

  // Accordion Tree State: Set of category IDs currently expanded
  const [expandedIds, setExpandedIds] = useState(new Set());

  // Modal State
  const [isModalOpen, setIsModalOpen] = useState(false);
  const [editingCategory, setEditingCategory] = useState(null);
  const [modalForm, setModalForm] = useState({
    name: '',
    slug: '',
    description: '',
    icon: 'Store',
    parent: null,
    sort_order: 0,
    is_active: true,
  });
  const [formSubmitting, setFormSubmitting] = useState(false);
  const [formError, setFormError] = useState('');

  // Delete State
  const [deleteTarget, setDeleteTarget] = useState(null);
  const [deleteError, setDeleteError] = useState('');
  const [deleting, setDeleting] = useState(false);

  // Fetch all categories for the full hierarchy tree
  const fetchCategories = useCallback(async () => {
    try {
      setLoading(true);
      setError(null);
      const data = await apiGetSellerHubCategories({});
      setAllCategories(Array.isArray(data) ? data : []);
    } catch (err) {
      setError(err?.data?.error || err.message || 'Failed to load catalog categories');
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    fetchCategories();
  }, [fetchCategories]);

  // Build Parent -> Children lookup Map and Category ID -> Category Map
  const { childrenMap, categoryMap, rootCategories } = useMemo(() => {
    const cMap = new Map();
    const catMap = new Map();
    const roots = [];

    // Register all categories
    allCategories.forEach((cat) => {
      catMap.set(cat.id, cat);
      if (!cMap.has(cat.id)) {
        cMap.set(cat.id, []);
      }
    });

    // Group children by parent_id
    allCategories.forEach((cat) => {
      if (cat.parent_id !== null && cat.parent_id !== undefined && catMap.has(cat.parent_id)) {
        const list = cMap.get(cat.parent_id) || [];
        list.push(cat);
        cMap.set(cat.parent_id, list);
      } else {
        roots.push(cat);
      }
    });

    return { childrenMap: cMap, categoryMap: catMap, rootCategories: roots };
  }, [allCategories]);

  // Sorting helper for category arrays
  const sortCategories = useCallback(
    (items) => {
      return [...items].sort((a, b) => {
        if (ordering === 'sort_order') {
          return (a.sort_order ?? 0) - (b.sort_order ?? 0);
        }
        if (ordering === '-sort_order') {
          return (b.sort_order ?? 0) - (a.sort_order ?? 0);
        }
        if (ordering === 'name') {
          return (a.name || '').localeCompare(b.name || '');
        }
        if (ordering === '-name') {
          return (b.name || '').localeCompare(a.name || '');
        }
        if (ordering === '-id') {
          return b.id - a.id;
        }
        return (a.sort_order ?? 0) - (b.sort_order ?? 0);
      });
    },
    [ordering]
  );

  // Search filter and auto-expand ancestors of matching items
  const { matchingIds, ancestorsOfMatches } = useMemo(() => {
    const trimmed = search.trim().toLowerCase();
    if (!trimmed) {
      return { matchingIds: null, ancestorsOfMatches: null };
    }

    const matches = new Set();
    const ancestors = new Set();

    allCategories.forEach((cat) => {
      const matchName = cat.name?.toLowerCase().includes(trimmed);
      const matchSlug = cat.slug?.toLowerCase().includes(trimmed);
      const matchDesc = cat.description?.toLowerCase().includes(trimmed);

      if (matchName || matchSlug || matchDesc) {
        matches.add(cat.id);

        // Traverse up ancestors and register for expansion
        let curr = cat;
        while (curr && curr.parent_id) {
          ancestors.add(curr.parent_id);
          curr = categoryMap.get(curr.parent_id);
        }
      }
    });

    return { matchingIds: matches, ancestorsOfMatches: ancestors };
  }, [search, allCategories, categoryMap]);

  // Auto-expand ancestors when search query is active
  useEffect(() => {
    if (ancestorsOfMatches && ancestorsOfMatches.size > 0) {
      setExpandedIds((prev) => {
        const next = new Set(prev);
        ancestorsOfMatches.forEach((id) => next.add(id));
        return next;
      });
    }
  }, [ancestorsOfMatches]);

  // Expand / Collapse Single Node
  const handleToggleExpand = (catId, e) => {
    if (e) {
      e.stopPropagation();
    }
    setExpandedIds((prev) => {
      const next = new Set(prev);
      if (next.has(catId)) {
        next.delete(catId);
      } else {
        next.add(catId);
      }
      return next;
    });
  };

  // Expand All / Collapse All
  const handleExpandAll = () => {
    const allParentIds = new Set();
    childrenMap.forEach((children, parentId) => {
      if (children.length > 0) {
        allParentIds.add(parentId);
      }
    });
    setExpandedIds(allParentIds);
  };

  const handleCollapseAll = () => {
    setExpandedIds(new Set());
  };

  // Generate Flattened Visible Rows for the Accordion Tree
  const visibleRows = useMemo(() => {
    const rows = [];

    const isStatusMatch = (cat) => {
      if (statusFilter === 'active') return Boolean(cat.is_active);
      if (statusFilter === 'inactive') return !cat.is_active;
      return true;
    };

    const traverse = (items, depth = 0, parentPath = []) => {
      const sorted = sortCategories(items);

      for (const cat of sorted) {
        const children = childrenMap.get(cat.id) || [];
        const hasChildren = children.length > 0;
        const isExpanded = expandedIds.has(cat.id);

        const isDirectMatch = matchingIds ? matchingIds.has(cat.id) : true;
        const isAncestorOfMatch = ancestorsOfMatches ? ancestorsOfMatches.has(cat.id) : false;

        // When searching, display item if it matches, is an ancestor of a match, or if search is empty
        const shouldIncludeInSearch = !matchingIds || isDirectMatch || isAncestorOfMatch;
        const matchesStatus = isStatusMatch(cat);

        if (shouldIncludeInSearch && (matchesStatus || isAncestorOfMatch)) {
          rows.push({
            ...cat,
            depth,
            hasChildren,
            isExpanded,
            isDirectMatch,
            childCount: children.length,
            parentPath,
          });
        }

        // If expanded (or forced expanded via search), traverse children
        if (hasChildren && (isExpanded || isAncestorOfMatch)) {
          traverse(children, depth + 1, [...parentPath, cat.name]);
        }
      }
    };

    traverse(rootCategories, 0, []);
    return rows;
  }, [
    rootCategories,
    childrenMap,
    expandedIds,
    sortCategories,
    statusFilter,
    matchingIds,
    ancestorsOfMatches,
  ]);

  // Open Create Modal (optionally with preselected parent for Add Subcategory)
  const handleOpenCreate = (preselectedParentId = null) => {
    setEditingCategory(null);
    setModalForm({
      name: '',
      slug: '',
      description: '',
      icon: 'Store',
      parent: preselectedParentId,
      sort_order: allCategories.length > 0 ? Math.max(...allCategories.map((c) => c.sort_order || 0)) + 1 : 1,
      is_active: true,
    });
    setFormError('');
    setIsModalOpen(true);
  };

  // Open Edit Modal
  const handleOpenEdit = (cat) => {
    setEditingCategory(cat);
    setModalForm({
      name: cat.name || '',
      slug: cat.slug || '',
      description: cat.description || '',
      icon: cat.icon || 'Store',
      parent: cat.parent_id || null,
      sort_order: cat.sort_order ?? 0,
      is_active: Boolean(cat.is_active),
    });
    setFormError('');
    setIsModalOpen(true);
  };

  const handleNameChange = (e) => {
    const val = e.target.value;
    if (!editingCategory) {
      const autoSlug = val
        .toLowerCase()
        .replace(/[^a-z0-9\s-]/g, '')
        .trim()
        .replace(/\s+/g, '-');
      setModalForm((prev) => ({ ...prev, name: val, slug: autoSlug }));
    } else {
      setModalForm((prev) => ({ ...prev, name: val }));
    }
  };

  const handleModalSubmit = async (e) => {
    e.preventDefault();
    if (!modalForm.name.trim()) {
      setFormError('Category name is required.');
      return;
    }

    try {
      setFormSubmitting(true);
      setFormError('');
      const payload = {
        ...modalForm,
        parent: modalForm.parent ? Number(modalForm.parent) : null,
      };

      if (editingCategory) {
        await apiUpdateSellerHubCategory(editingCategory.id, payload);
      } else {
        const created = await apiCreateSellerHubCategory(payload);
        // Automatically expand the parent branch if adding a subcategory
        if (payload.parent) {
          setExpandedIds((prev) => new Set([...prev, payload.parent]));
        }
      }
      setIsModalOpen(false);
      await fetchCategories();
    } catch (err) {
      const fieldErrors = err?.data?.details;
      if (fieldErrors && typeof fieldErrors === 'object') {
        const firstKey = Object.keys(fieldErrors)[0];
        const msg = Array.isArray(fieldErrors[firstKey]) ? fieldErrors[firstKey][0] : fieldErrors[firstKey];
        setFormError(`${firstKey}: ${msg}`);
      } else {
        setFormError(err?.data?.error || err?.message || 'Failed to save category.');
      }
    } finally {
      setFormSubmitting(false);
    }
  };

  const handleToggleActive = async (cat, e) => {
    if (e) e.stopPropagation();
    if (!isSuperAdmin) return;
    try {
      await apiUpdateSellerHubCategory(cat.id, { is_active: !cat.is_active });
      setAllCategories((prev) =>
        prev.map((c) => (c.id === cat.id ? { ...c, is_active: !c.is_active } : c))
      );
    } catch (err) {
      setError(err?.data?.error || 'Failed to update category status.');
    }
  };

  const handleDeleteConfirm = async () => {
    if (!deleteTarget) return;
    try {
      setDeleting(true);
      setDeleteError('');
      await apiDeleteSellerHubCategory(deleteTarget.id);
      setDeleteTarget(null);
      await fetchCategories();
    } catch (err) {
      setDeleteError(err?.data?.error || err.message || 'Failed to delete category.');
    } finally {
      setDeleting(false);
    }
  };

  // Eligible parent categories for the dropdown: exclude current category and its descendants
  const eligibleParents = useMemo(() => {
    if (!editingCategory) return allCategories;
    const excludeIds = new Set([editingCategory.id]);

    let added = true;
    while (added) {
      added = false;
      for (const c of allCategories) {
        if (c.parent_id && excludeIds.has(c.parent_id) && !excludeIds.has(c.id)) {
          excludeIds.add(c.id);
          added = true;
        }
      }
    }
    return allCategories.filter((c) => !excludeIds.has(c.id));
  }, [allCategories, editingCategory]);

  return (
    <div className="flex min-h-screen bg-slate-100 font-sans text-slate-800">
      <Sidebar />

      <main className="flex-1 min-w-0 flex flex-col">
        {/* Header */}
        <header className="bg-white border-b border-slate-200 sticky top-0 z-10 px-8 py-5 flex items-center justify-between shadow-sm">
          <div className="flex items-center gap-3">
            <span className="p-2 bg-emerald-50 text-emerald-600 rounded-lg">
              <Layers className="w-5 h-5" />
            </span>
            <div>
              <h1 className="text-xl font-bold text-slate-900 tracking-tight">
                Catalog Categories
              </h1>
              <p className="text-xs text-slate-500 mt-0.5">
                Organize products and services in a multi-level folder tree
              </p>
            </div>
          </div>

          <div className="flex items-center gap-3">
            <button
              type="button"
              onClick={fetchCategories}
              disabled={loading}
              className="p-2 text-slate-600 hover:text-slate-900 hover:bg-slate-100 rounded-lg transition-colors border border-slate-200"
              title="Refresh categories"
            >
              <RefreshCw className={`w-4 h-4 ${loading ? 'animate-spin text-emerald-600' : ''}`} />
            </button>

            {isSuperAdmin && (
              <button
                type="button"
                onClick={() => handleOpenCreate(null)}
                className="inline-flex items-center gap-2 px-4 py-2 bg-emerald-600 hover:bg-emerald-700 text-white rounded-lg text-sm font-semibold shadow-sm transition-colors"
              >
                <Plus className="w-4 h-4" />
                <span>Add Category</span>
              </button>
            )}
          </div>
        </header>

        {/* Content Area */}
        <div className="p-8 space-y-6 flex-1">
          {error && (
            <div className="p-4 bg-red-50 border border-red-200 rounded-xl flex items-start gap-3 text-red-700 text-sm animate-fadeIn">
              <AlertCircle className="w-5 h-5 shrink-0 mt-0.5 text-red-500" />
              <div className="flex-1">
                <p className="font-semibold">Error</p>
                <p className="text-xs text-red-600 mt-0.5">{error}</p>
              </div>
              <button
                type="button"
                onClick={() => setError(null)}
                className="text-red-400 hover:text-red-600"
              >
                <X className="w-4 h-4" />
              </button>
            </div>
          )}

          {/* Filters & Tree Controls Bar */}
          <div className="bg-white p-4 rounded-xl border border-slate-200 shadow-sm flex flex-col md:flex-row items-center justify-between gap-4">
            <div className="relative w-full md:w-80">
              <Search className="w-4 h-4 absolute left-3 top-1/2 -translate-y-1/2 text-slate-400" />
              <input
                type="text"
                placeholder="Search categories across hierarchy..."
                value={search}
                onChange={(e) => setSearch(e.target.value)}
                className="w-full pl-9 pr-4 py-2 bg-slate-50 border border-slate-300 rounded-lg text-sm text-slate-800 placeholder-slate-400 focus:outline-none focus:ring-2 focus:ring-emerald-500 focus:bg-white transition-all"
              />
              {search && (
                <button
                  type="button"
                  onClick={() => setSearch('')}
                  className="absolute right-3 top-1/2 -translate-y-1/2 text-slate-400 hover:text-slate-600"
                >
                  <X className="w-3.5 h-3.5" />
                </button>
              )}
            </div>

            <div className="flex items-center gap-3 w-full md:w-auto flex-wrap justify-between md:justify-end">
              {/* Expand / Collapse All Controls */}
              <div className="flex items-center gap-1 bg-slate-100 p-1 rounded-lg border border-slate-200 text-xs font-semibold">
                <button
                  type="button"
                  onClick={handleExpandAll}
                  className="inline-flex items-center gap-1 px-2.5 py-1 text-slate-700 hover:text-emerald-700 hover:bg-white rounded transition-all"
                  title="Expand all tree branches"
                >
                  <Maximize2 className="w-3.5 h-3.5" />
                  <span>Expand All</span>
                </button>
                <button
                  type="button"
                  onClick={handleCollapseAll}
                  className="inline-flex items-center gap-1 px-2.5 py-1 text-slate-700 hover:text-slate-900 hover:bg-white rounded transition-all"
                  title="Collapse all tree branches"
                >
                  <Minimize2 className="w-3.5 h-3.5" />
                  <span>Collapse All</span>
                </button>
              </div>

              {/* Status Filter */}
              <div className="flex items-center gap-1 bg-slate-100 p-1 rounded-lg border border-slate-200 text-xs font-semibold">
                <button
                  type="button"
                  onClick={() => setStatusFilter('all')}
                  className={`px-3 py-1 rounded-md transition-all ${
                    statusFilter === 'all'
                      ? 'bg-white text-slate-800 shadow-sm'
                      : 'text-slate-600 hover:text-slate-900'
                  }`}
                >
                  All
                </button>
                <button
                  type="button"
                  onClick={() => setStatusFilter('active')}
                  className={`px-3 py-1 rounded-md transition-all ${
                    statusFilter === 'active'
                      ? 'bg-emerald-600 text-white shadow-sm'
                      : 'text-slate-600 hover:text-slate-900'
                  }`}
                >
                  Active
                </button>
                <button
                  type="button"
                  onClick={() => setStatusFilter('inactive')}
                  className={`px-3 py-1 rounded-md transition-all ${
                    statusFilter === 'inactive'
                      ? 'bg-slate-700 text-white shadow-sm'
                      : 'text-slate-600 hover:text-slate-900'
                  }`}
                >
                  Inactive
                </button>
              </div>

              {/* Ordering */}
              <div className="flex items-center gap-1.5 text-xs font-medium text-slate-500">
                <ArrowUpDown className="w-3.5 h-3.5 text-slate-400" />
                <select
                  value={ordering}
                  onChange={(e) => setOrdering(e.target.value)}
                  className="bg-white border border-slate-300 rounded-lg px-2.5 py-1.5 text-slate-700 text-xs focus:outline-none focus:ring-2 focus:ring-emerald-500"
                >
                  <option value="sort_order">Sort Order (Asc)</option>
                  <option value="-sort_order">Sort Order (Desc)</option>
                  <option value="name">Name (A-Z)</option>
                  <option value="-name">Name (Z-A)</option>
                  <option value="-id">Recently Added</option>
                </select>
              </div>
            </div>
          </div>

          {/* Accordion Tree Table */}
          <div className="bg-white rounded-xl border border-slate-200 shadow-sm overflow-hidden">
            {loading ? (
              <div className="p-16 flex flex-col items-center justify-center text-slate-400 gap-3">
                <RefreshCw className="w-8 h-8 animate-spin text-emerald-600" />
                <span className="text-sm font-medium">Loading catalog categories tree...</span>
              </div>
            ) : visibleRows.length === 0 ? (
              <div className="p-16 flex flex-col items-center justify-center text-center">
                <div className="p-4 bg-slate-100 rounded-full text-slate-400 mb-3">
                  <FolderTree className="w-8 h-8" />
                </div>
                <h3 className="text-base font-bold text-slate-800">
                  {search ? 'No categories match your search' : 'No catalog categories found'}
                </h3>
                <p className="text-xs text-slate-500 max-w-sm mt-1 mb-4">
                  {search
                    ? `No category found matching "${search}". Try adjusting your search query.`
                    : 'Start organizing your catalog by adding top-level root categories.'}
                </p>
                {isSuperAdmin && (
                  <button
                    type="button"
                    onClick={() => handleOpenCreate(null)}
                    className="inline-flex items-center gap-1.5 px-3.5 py-2 bg-emerald-600 hover:bg-emerald-700 text-white rounded-lg text-xs font-semibold shadow-sm transition-colors"
                  >
                    <Plus className="w-4 h-4" />
                    <span>Create First Category</span>
                  </button>
                )}
              </div>
            ) : (
              <div className="overflow-x-auto">
                <table className="w-full text-left border-collapse text-xs">
                  <thead>
                    <tr className="bg-slate-50 border-b border-slate-200 text-slate-500 font-semibold uppercase tracking-wider text-[11px]">
                      <th className="py-3.5 px-6 min-w-[320px]">Category Hierarchy</th>
                      <th className="py-3.5 px-4">Slug</th>
                      <th className="py-3.5 px-4">Linked Data</th>
                      <th className="py-3.5 px-4 text-center">Sort Order</th>
                      <th className="py-3.5 px-4 text-center">Status</th>
                      <th className="py-3.5 px-6 text-right min-w-[180px]">Actions</th>
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-slate-100 font-normal">
                    {visibleRows.map((cat) => {
                      const IconComp = AVAILABLE_ICONS.find((i) => i.name === cat.icon)?.icon || Store;
                      const isRoot = cat.depth === 0;
                      const indentPx = cat.depth * 28;

                      return (
                        <tr
                          key={cat.id}
                          className={`transition-colors group ${
                            cat.isExpanded
                              ? 'bg-emerald-50/20 hover:bg-emerald-50/40'
                              : cat.depth > 0
                              ? 'bg-slate-50/30 hover:bg-slate-50/80'
                              : 'hover:bg-slate-50/80'
                          } ${cat.isDirectMatch && search ? 'bg-amber-50/40' : ''}`}
                        >
                          {/* Folder Tree Cell with Expand Chevron, Guide Lines & Indentation */}
                          <td className="py-3.5 px-6">
                            <div
                              className="flex items-center relative"
                              style={{ paddingLeft: `${indentPx}px` }}
                            >
                              {/* Branch Connector Line for Nested Items */}
                              {cat.depth > 0 && (
                                <div
                                  className="absolute border-l-2 border-b-2 border-slate-300 rounded-bl-md pointer-events-none"
                                  style={{
                                    left: `${indentPx - 16}px`,
                                    top: '-12px',
                                    width: '12px',
                                    height: '28px',
                                  }}
                                />
                              )}

                              {/* Accordion Expand / Collapse Chevron Button */}
                              {cat.hasChildren ? (
                                <button
                                  type="button"
                                  onClick={(e) => handleToggleExpand(cat.id, e)}
                                  onKeyDown={(e) => {
                                    if (e.key === 'Enter' || e.key === ' ') {
                                      e.preventDefault();
                                      handleToggleExpand(cat.id, e);
                                    }
                                  }}
                                  aria-expanded={cat.isExpanded}
                                  aria-label={`${cat.isExpanded ? 'Collapse' : 'Expand'} ${cat.name}`}
                                  className={`p-1 mr-1.5 rounded-md transition-transform duration-150 focus:outline-none focus:ring-2 focus:ring-emerald-500 shrink-0 ${
                                    cat.isExpanded
                                      ? 'text-emerald-700 bg-emerald-100 rotate-90'
                                      : 'text-slate-500 hover:text-slate-800 hover:bg-slate-200'
                                  }`}
                                  title={`${cat.isExpanded ? 'Collapse' : 'Expand'} subcategories`}
                                >
                                  <ChevronRight className="w-4 h-4" />
                                </button>
                              ) : (
                                <div className="w-6 mr-1.5 flex items-center justify-center shrink-0">
                                  {cat.depth > 0 ? (
                                    <CornerDownRight className="w-3.5 h-3.5 text-slate-300" />
                                  ) : (
                                    <span className="w-1.5 h-1.5 rounded-full bg-slate-300" />
                                  )}
                                </div>
                              )}

                              {/* Category Icon / Folder Icon */}
                              <div
                                onClick={(e) => cat.hasChildren && handleToggleExpand(cat.id, e)}
                                className={`p-1.5 rounded-lg border shrink-0 mr-2.5 transition-colors ${
                                  cat.hasChildren
                                    ? cat.isExpanded
                                      ? 'bg-emerald-100 border-emerald-300 text-emerald-700'
                                      : 'bg-amber-50 border-amber-200 text-amber-600'
                                    : cat.is_active
                                    ? 'bg-emerald-50 border-emerald-200 text-emerald-600'
                                    : 'bg-slate-100 border-slate-200 text-slate-400'
                                } ${cat.hasChildren ? 'cursor-pointer' : ''}`}
                                title={cat.hasChildren ? (cat.isExpanded ? 'Collapse' : 'Expand') : cat.icon}
                              >
                                {cat.hasChildren ? (
                                  cat.isExpanded ? (
                                    <FolderOpen className="w-4 h-4" />
                                  ) : (
                                    <Folder className="w-4 h-4" />
                                  )
                                ) : (
                                  <IconComp className="w-4 h-4" />
                                )}
                              </div>

                              {/* Name, Subcategory Count & Description */}
                              <div className="min-w-0 flex-1">
                                <div className="flex items-center gap-2 flex-wrap">
                                  <button
                                    type="button"
                                    onClick={(e) => cat.hasChildren && handleToggleExpand(cat.id, e)}
                                    className={`font-semibold text-left transition-colors text-xs truncate ${
                                      isRoot ? 'text-slate-900 text-sm font-bold' : 'text-slate-800'
                                    } ${
                                      cat.hasChildren
                                        ? 'hover:text-emerald-700 cursor-pointer'
                                        : 'hover:text-emerald-600'
                                    }`}
                                  >
                                    {cat.name}
                                  </button>

                                  {/* Subcategories count badge */}
                                  {cat.hasChildren && (
                                    <span
                                      onClick={(e) => handleToggleExpand(cat.id, e)}
                                      className={`inline-flex items-center gap-1 text-[11px] font-medium px-2 py-0.5 rounded-full cursor-pointer transition-colors ${
                                        cat.isExpanded
                                          ? 'bg-emerald-100 text-emerald-800 border border-emerald-200'
                                          : 'bg-slate-100 text-slate-600 border border-slate-200 hover:bg-slate-200'
                                      }`}
                                      title="Click to toggle child branches"
                                    >
                                      <span>
                                        {cat.childCount} {cat.childCount === 1 ? 'subcategory' : 'subcategories'}
                                      </span>
                                    </span>
                                  )}

                                  {/* Parent Path / Breadcrumb indicator during search */}
                                  {search && cat.parentPath && cat.parentPath.length > 0 && (
                                    <span className="text-[10px] text-slate-400 font-mono">
                                      under {cat.parentPath.join(' › ')}
                                    </span>
                                  )}
                                </div>

                                {cat.description && (
                                  <p className="text-slate-500 text-[11px] truncate max-w-sm mt-0.5">
                                    {cat.description}
                                  </p>
                                )}
                              </div>
                            </div>
                          </td>

                          {/* Slug */}
                          <td className="py-3.5 px-4 font-mono text-[11px] text-slate-600">
                            <span className="bg-slate-100 px-2 py-0.5 rounded border border-slate-200">
                              {cat.slug}
                            </span>
                          </td>

                          {/* Linked data (Services & Inventory items) */}
                          <td className="py-3.5 px-4 text-slate-600">
                            <div className="flex flex-col gap-0.5 text-[11px]">
                              <span>{cat.services_count || 0} services</span>
                              <span className="text-slate-400 font-mono">
                                {cat.inventory_items_count || 0} items
                              </span>
                            </div>
                          </td>

                          {/* Sort Order */}
                          <td className="py-3.5 px-4 text-center font-mono font-medium text-slate-600">
                            {cat.sort_order ?? 0}
                          </td>

                          {/* Status & Active Toggle */}
                          <td className="py-3.5 px-4 text-center">
                            <button
                              type="button"
                              onClick={(e) => handleToggleActive(cat, e)}
                              disabled={!isSuperAdmin}
                              className={`inline-flex items-center gap-1 px-2.5 py-0.5 rounded-full text-xs font-semibold transition-all ${
                                cat.is_active
                                  ? 'bg-emerald-50 text-emerald-700 border border-emerald-200 hover:bg-emerald-100'
                                  : 'bg-slate-100 text-slate-500 border border-slate-200 hover:bg-slate-200'
                              } ${!isSuperAdmin ? 'cursor-default opacity-80' : 'cursor-pointer'}`}
                              title={isSuperAdmin ? 'Click to toggle active/inactive' : ''}
                            >
                              {cat.is_active ? (
                                <>
                                  <CheckCircle2 className="w-3 h-3 text-emerald-600" />
                                  <span>Active</span>
                                </>
                              ) : (
                                <>
                                  <XCircle className="w-3 h-3 text-slate-400" />
                                  <span>Inactive</span>
                                </>
                              )}
                            </button>
                          </td>

                          {/* Actions: + Subcategory, Edit, Delete */}
                          <td className="py-3.5 px-6 text-right">
                            <div className="flex items-center justify-end gap-1">
                              {isSuperAdmin && (
                                <button
                                  type="button"
                                  onClick={() => handleOpenCreate(cat.id)}
                                  className="inline-flex items-center gap-1 px-2.5 py-1 text-slate-700 bg-slate-100 hover:bg-emerald-50 hover:text-emerald-700 hover:border-emerald-300 border border-slate-200 rounded-lg text-xs font-medium transition-colors"
                                  title={`Add a subcategory inside "${cat.name}"`}
                                >
                                  <Plus className="w-3 h-3 text-emerald-600" />
                                  <span>Subcategory</span>
                                </button>
                              )}

                              {isSuperAdmin && (
                                <>
                                  <button
                                    type="button"
                                    onClick={() => handleOpenEdit(cat)}
                                    className="p-1.5 text-slate-600 hover:text-slate-900 hover:bg-slate-100 rounded-lg transition-colors"
                                    title="Edit category"
                                  >
                                    <Edit2 className="w-4 h-4" />
                                  </button>

                                  <button
                                    type="button"
                                    onClick={() => {
                                      setDeleteTarget(cat);
                                      setDeleteError('');
                                    }}
                                    className="p-1.5 text-slate-400 hover:text-red-600 hover:bg-red-50 rounded-lg transition-colors"
                                    title="Delete category"
                                  >
                                    <Trash2 className="w-4 h-4" />
                                  </button>
                                </>
                              )}
                            </div>
                          </td>
                        </tr>
                      );
                    })}
                  </tbody>
                </table>
              </div>
            )}
          </div>
        </div>
      </main>

      {/* ── CREATE / EDIT CATEGORY MODAL ── */}
      {isModalOpen && (
        <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-slate-900/60 backdrop-blur-sm animate-fadeIn">
          <div className="bg-white rounded-2xl shadow-xl w-full max-w-lg border border-slate-200 overflow-hidden flex flex-col max-h-[90vh]">
            <div className="px-6 py-4 border-b border-slate-200 flex items-center justify-between bg-slate-50">
              <div className="flex items-center gap-2">
                <span className="p-2 bg-emerald-100 text-emerald-700 rounded-lg">
                  <Layers className="w-4 h-4" />
                </span>
                <h3 className="font-bold text-slate-900 text-base">
                  {editingCategory
                    ? 'Edit Catalog Category'
                    : modalForm.parent
                    ? `Add Subcategory in "${categoryMap.get(modalForm.parent)?.name || 'Parent'}"`
                    : 'Add New Root Category'}
                </h3>
              </div>
              <button
                type="button"
                onClick={() => setIsModalOpen(false)}
                className="text-slate-400 hover:text-slate-600 p-1 rounded-lg"
              >
                <X className="w-5 h-5" />
              </button>
            </div>

            <form onSubmit={handleModalSubmit} className="flex-1 overflow-y-auto p-6 space-y-4">
              {formError && (
                <div className="p-3 bg-red-50 border border-red-200 rounded-lg text-red-700 text-xs flex items-start gap-2">
                  <AlertCircle className="w-4 h-4 shrink-0 mt-0.5 text-red-500" />
                  <span>{formError}</span>
                </div>
              )}

              {/* Parent Category Selector */}
              <div>
                <label className="block text-xs font-semibold text-slate-700 mb-1">
                  Parent Category
                </label>
                <select
                  value={modalForm.parent ?? ''}
                  onChange={(e) =>
                    setModalForm((prev) => ({
                      ...prev,
                      parent: e.target.value ? Number(e.target.value) : null,
                    }))
                  }
                  className="w-full px-3 py-2 bg-slate-50 border border-slate-300 rounded-lg text-xs text-slate-800 focus:outline-none focus:ring-2 focus:ring-emerald-500 focus:bg-white"
                >
                  <option value="">None (Top-Level Root Category)</option>
                  {eligibleParents.map((p) => {
                    const indent = '— '.repeat(p.level ?? (p.ancestors ? p.ancestors.length : 0));
                    return (
                      <option key={p.id} value={p.id}>
                        {indent}
                        {p.name} {p.level ? `(Level ${p.level})` : ''}
                      </option>
                    );
                  })}
                </select>
                <p className="text-[11px] text-slate-400 mt-1">
                  Choose where this category resides in the tree (e.g. Grocery → Oil → Sunflower Oil).
                </p>
              </div>

              <div>
                <label className="block text-xs font-semibold text-slate-700 mb-1">
                  Category Name <span className="text-red-500">*</span>
                </label>
                <input
                  type="text"
                  required
                  placeholder="e.g. Sunflower Oil, Dhals, Exotic Fruits"
                  value={modalForm.name}
                  onChange={handleNameChange}
                  className="w-full px-3 py-2 bg-slate-50 border border-slate-300 rounded-lg text-xs text-slate-800 focus:outline-none focus:ring-2 focus:ring-emerald-500 focus:bg-white"
                />
              </div>

              <div>
                <label className="block text-xs font-semibold text-slate-700 mb-1">
                  Slug (URL Identifier)
                </label>
                <input
                  type="text"
                  placeholder="e.g. sunflower-oil"
                  value={modalForm.slug}
                  onChange={(e) => setModalForm((prev) => ({ ...prev, slug: e.target.value }))}
                  className="w-full px-3 py-2 bg-slate-50 border border-slate-300 rounded-lg text-xs font-mono text-slate-800 focus:outline-none focus:ring-2 focus:ring-emerald-500 focus:bg-white"
                />
              </div>

              <div>
                <label className="block text-xs font-semibold text-slate-700 mb-1">
                  Description
                </label>
                <textarea
                  rows={3}
                  placeholder="Brief summary of items or services under this category..."
                  value={modalForm.description}
                  onChange={(e) => setModalForm((prev) => ({ ...prev, description: e.target.value }))}
                  className="w-full px-3 py-2 bg-slate-50 border border-slate-300 rounded-lg text-xs text-slate-800 focus:outline-none focus:ring-2 focus:ring-emerald-500 focus:bg-white resize-none"
                />
              </div>

              {/* Icon Selector */}
              <div>
                <label className="block text-xs font-semibold text-slate-700 mb-1.5">
                  Category Icon
                </label>
                <div className="grid grid-cols-4 gap-2">
                  {AVAILABLE_ICONS.map(({ name, icon: Icon }) => (
                    <button
                      key={name}
                      type="button"
                      onClick={() => setModalForm((prev) => ({ ...prev, icon: name }))}
                      className={`p-2.5 rounded-lg border text-xs font-medium flex flex-col items-center gap-1.5 transition-all ${
                        modalForm.icon === name
                          ? 'bg-emerald-50 border-emerald-500 text-emerald-700 ring-2 ring-emerald-500/20 shadow-sm'
                          : 'bg-slate-50 border-slate-200 text-slate-600 hover:bg-slate-100'
                      }`}
                    >
                      <Icon className="w-4 h-4" />
                      <span className="text-[10px] truncate w-full text-center">{name}</span>
                    </button>
                  ))}
                </div>
              </div>

              <div className="grid grid-cols-2 gap-4">
                <div>
                  <label className="block text-xs font-semibold text-slate-700 mb-1">
                    Sort Order
                  </label>
                  <input
                    type="number"
                    value={modalForm.sort_order}
                    onChange={(e) =>
                      setModalForm((prev) => ({
                        ...prev,
                        sort_order: parseInt(e.target.value, 10) || 0,
                      }))
                    }
                    className="w-full px-3 py-2 bg-slate-50 border border-slate-300 rounded-lg text-xs text-slate-800 focus:outline-none focus:ring-2 focus:ring-emerald-500 focus:bg-white font-mono"
                  />
                </div>

                <div>
                  <label className="block text-xs font-semibold text-slate-700 mb-1">
                    Initial Status
                  </label>
                  <div className="flex items-center gap-3 pt-2">
                    <label className="inline-flex items-center gap-1.5 text-xs text-slate-700 cursor-pointer">
                      <input
                        type="checkbox"
                        checked={modalForm.is_active}
                        onChange={(e) =>
                          setModalForm((prev) => ({ ...prev, is_active: e.target.checked }))
                        }
                        className="rounded border-slate-300 text-emerald-600 focus:ring-emerald-500 w-4 h-4"
                      />
                      <span className="font-medium">Active (Visible in Catalog)</span>
                    </label>
                  </div>
                </div>
              </div>

              <div className="pt-4 border-t border-slate-200 flex items-center justify-end gap-2">
                <button
                  type="button"
                  onClick={() => setIsModalOpen(false)}
                  className="px-4 py-2 text-xs font-semibold text-slate-700 bg-slate-100 hover:bg-slate-200 rounded-lg transition-colors"
                >
                  Cancel
                </button>
                <button
                  type="submit"
                  disabled={formSubmitting}
                  className="px-5 py-2 text-xs font-semibold text-white bg-emerald-600 hover:bg-emerald-700 rounded-lg shadow-sm transition-colors flex items-center gap-1.5"
                >
                  {formSubmitting && <RefreshCw className="w-3.5 h-3.5 animate-spin" />}
                  <span>{editingCategory ? 'Save Changes' : 'Create Category'}</span>
                </button>
              </div>
            </form>
          </div>
        </div>
      )}

      {/* ── SAFE DELETION CONFIRMATION MODAL ── */}
      {deleteTarget && (
        <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-slate-900/60 backdrop-blur-sm animate-fadeIn">
          <div className="bg-white rounded-2xl shadow-xl w-full max-w-md border border-slate-200 overflow-hidden p-6 space-y-4">
            <div className="flex items-center gap-3 text-red-600">
              <span className="p-2.5 bg-red-50 rounded-xl border border-red-100">
                <AlertCircle className="w-6 h-6 text-red-600" />
              </span>
              <div>
                <h3 className="font-bold text-slate-900 text-base">Delete Category?</h3>
                <p className="text-xs text-slate-500">Safe deletion checks apply</p>
              </div>
            </div>

            <p className="text-xs text-slate-600 leading-relaxed">
              Are you sure you want to permanently delete{' '}
              <strong className="text-slate-900 font-semibold">"{deleteTarget.name}"</strong>?
            </p>

            {(deleteTarget.children_count > 0 ||
              deleteTarget.services_count > 0 ||
              deleteTarget.inventory_items_count > 0) && (
              <div className="p-3 bg-amber-50 border border-amber-200 rounded-xl text-amber-800 text-xs space-y-1">
                <p className="font-bold flex items-center gap-1.5">
                  <Info className="w-3.5 h-3.5" />
                  Protected Category
                </p>
                <p className="text-[11px] text-amber-700">
                  This category contains{' '}
                  {deleteTarget.children_count > 0 && (
                    <span>
                      <strong>{deleteTarget.children_count} subcategories</strong>,{' '}
                    </span>
                  )}
                  {deleteTarget.services_count > 0 && (
                    <span>
                      <strong>{deleteTarget.services_count} services</strong>,{' '}
                    </span>
                  )}
                  {deleteTarget.inventory_items_count > 0 && (
                    <span>
                      <strong>{deleteTarget.inventory_items_count} items</strong>
                    </span>
                  )}
                  . You must reassign or remove them before deleting.
                </p>
              </div>
            )}

            {deleteError && (
              <div className="p-3 bg-red-50 border border-red-200 rounded-lg text-red-700 text-xs flex items-start gap-2">
                <AlertCircle className="w-4 h-4 shrink-0 mt-0.5 text-red-500" />
                <span>{deleteError}</span>
              </div>
            )}

            <div className="flex items-center justify-end gap-2 pt-2 border-t border-slate-100">
              <button
                type="button"
                onClick={() => setDeleteTarget(null)}
                className="px-4 py-2 text-xs font-semibold text-slate-700 bg-slate-100 hover:bg-slate-200 rounded-lg transition-colors"
              >
                Cancel
              </button>
              <button
                type="button"
                onClick={handleDeleteConfirm}
                disabled={deleting}
                className="px-4 py-2 text-xs font-semibold text-white bg-red-600 hover:bg-red-700 rounded-lg shadow-sm transition-colors flex items-center gap-1.5"
              >
                {deleting && <RefreshCw className="w-3.5 h-3.5 animate-spin" />}
                <span>Confirm Delete</span>
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}

