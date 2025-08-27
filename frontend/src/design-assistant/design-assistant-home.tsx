import {
    DesignAssistantHeader,
    DesignAssistantError,
    DesignAssistantNoParts,
    DesignAssistantLoading,
    DesignAssistantContent
} from "./components";
import {
    useDesignAssistantDocumentsQuery,
    useBomDataQuery,
    useRefreshCooldownQuery
} from "../queries";
import { useSearch } from "@tanstack/react-router";
import { useState, useEffect, useCallback, useMemo } from "react";
import { useQueryClient } from "@tanstack/react-query";
import { getCotsCategory } from "../services/cots-service";

export function DesignAssistantHome() {
    const search = useSearch({ from: "/app/designassistant/" });
    const [expandedParts, setExpandedParts] = useState<Set<string>>(new Set());
    const [isUpdating, setIsUpdating] = useState(false);
    const [countdownSeconds, setCountdownSeconds] = useState(0);
    const [forceRefresh, setForceRefresh] = useState(false);
    const [showDebugButtons, setShowDebugButtons] = useState(false);
    const [showOnlyMissingWeight, setShowOnlyMissingWeight] = useState(false);
    const [sortByImported, setSortByImported] = useState<'none' | 'imported-first' | 'current-first'>('none');
    const [searchTerm, setSearchTerm] = useState('');
    const [vendorFilter, setVendorFilter] = useState('');
    const queryClient = useQueryClient();

    const bomDataQuery = useBomDataQuery({
        ...(search as Record<string, any>),
        forceRefresh: forceRefresh
    });
    const bomData = bomDataQuery.data;
    const refreshCooldownQuery = useRefreshCooldownQuery(search as any);
    const cooldownData = refreshCooldownQuery.data;

    // Debug logging for BOM data changes
    useEffect(() => {
        if (bomData) {
            console.log("BOM data updated:", {
                isCached: bomData.cacheInfo?.isCached,
                lastUpdated: bomData.cacheInfo?.lastUpdated,
                ageHours: bomData.cacheInfo?.ageHours,
                forceRefresh: forceRefresh
            });
        }
    }, [bomData, forceRefresh]);

    // Debug logging for forceRefresh state changes
    useEffect(() => {
        console.log("forceRefresh state changed to:", forceRefresh);
    }, [forceRefresh]);

    // Update countdown timer every second
    useEffect(() => {
        let interval: ReturnType<typeof setInterval> | null = null;
        const shouldRunCountdown = countdownSeconds > 0;

        if (shouldRunCountdown) {
            interval = setInterval(() => {
                setCountdownSeconds((prev) => {
                    const newValue = prev <= 1 ? 0 : prev - 1;
                    return newValue;
                });
            }, 1000);
        }

        return () => {
            if (interval) {
                clearInterval(interval);
            }
        };
    }, [countdownSeconds]);

    // Set initial countdown when cooldown data changes
    useEffect(() => {
        if (
            cooldownData &&
            !cooldownData.canRefresh &&
            cooldownData.remainingSeconds > 0
        ) {
            setCountdownSeconds(cooldownData.remainingSeconds);
        }
    }, [cooldownData]);

    const {
        data: analysis,
        isLoading: analysisLoading,
        error: analysisError
    } = useDesignAssistantDocumentsQuery({
        elementType: (search as any).elementType,
        documentId: (search as any).documentId,
        instanceType: (search as any).instanceType,
        instanceId: (search as any).instanceId,
        elementId: (search as any).elementId
    });

    const isLoading = analysisLoading || bomDataQuery.isLoading;
    const hasError = analysisError || bomDataQuery.error;
    
    // Check if we're in a Part Studio context
    const isPartStudio = (search as any)?.elementType === 'PARTSTUDIO';

    // Data processing logic - memoized for performance
    const processedData = useMemo(() => {
        const allParts = bomData?.missingMaterialParts || analysis?.documents || [];
        const hasOriginCube = allParts.some((doc: any) =>
            (doc.name || doc.part_name || "").toLowerCase().includes("origin")
        );

        // Filter out origin parts and breakdown items, keep main assembly entries
        const parts = allParts.filter((doc: any) => {
            // Skip origin parts
            if (
                (doc.name || doc.part_name || "")
                    .toLowerCase()
                    .includes("origin")
            ) {
                return false;
            }

            // Skip breakdown items (items with decimal numbers like "15.1", "15.2")
            if (
                doc.item &&
                typeof doc.item === "string" &&
                doc.item.includes(".")
            ) {
                return false;
            }

            return true;
        });

        // Group parts by document source
        const currentDocumentParts = parts.filter(
            (doc: any) => doc.isCurrentDocument
        );
        const importedParts = parts.filter((doc: any) => !doc.isCurrentDocument);

        // Create a map of breakdown items for each main part
        const breakdownMap = new Map();
        allParts.forEach((doc: any) => {
            if (
                doc.item &&
                typeof doc.item === "string" &&
                doc.item.includes(".")
            ) {
                const mainItem = doc.item.split(".")[0];
                if (!breakdownMap.has(mainItem)) {
                    breakdownMap.set(mainItem, []);
                }
                breakdownMap.get(mainItem).push(doc);
            }
        });

        // Calculate total mass from individual part weights
        const totalMassLbs = parts.reduce((total: number, part: any) => {
            const mass = part.mass_lb || 0;
            const quantity = part.quantity || 1;
            return total + mass * quantity;
        }, 0);

        const weightData = {
            unit: "lb",
            total_weight: totalMassLbs,
            rows_counted: parts.length,
            rows_skipped: 0
        };

        // Enhanced missing weight detection for hierarchical structures
        const isMissingWeight = (doc: any) => {
            const mass = doc.mass_lb;
            const calculatedMass = doc.calculatedMass;
            const hasDirectMissingWeight = (mass === null || mass === undefined || mass === "") && 
                                          (calculatedMass === null || calculatedMass === undefined || calculatedMass === "");
            const hasChildrenMissingWeight = doc.hasChildrenMissingMass || false;
            
            // Only include if: direct missing weight or children have missing weight (not material issues)
            return hasDirectMissingWeight || hasChildrenMissingWeight;
        };

        // Helper function to count missing materials in subassembly children
        const countMissingInChildren = (part: any, allParts: any[]): { missingMaterial: number; missingWeight: number } => {
            let missingMaterial = 0;
            let missingWeight = 0;
            
            if (part.children && Array.isArray(part.children)) {
                part.children.forEach((childId: string) => {
                    const child = allParts.find(p => p.item === childId);
                    if (child) {
                        // Count direct issues
                        if (child.missingMaterial) missingMaterial++;
                        
                        const hasMissingWeight = (child.mass_lb === null || child.mass_lb === undefined || child.mass_lb === "") && 
                            (child.calculatedMass === null || child.calculatedMass === undefined || child.calculatedMass === "");
                        if (hasMissingWeight) missingWeight++;
                        
                        // Recursively count in nested children
                        const childCounts = countMissingInChildren(child, allParts);
                        missingMaterial += childCounts.missingMaterial;
                        missingWeight += childCounts.missingWeight;
                    }
                });
            }
            
            return { missingMaterial, missingWeight };
        };

        // Flatten hierarchy to include all parts (parents and children)
        const flattenHierarchy = (parts: any[]): any[] => {
            const flattened: any[] = [];
            const processed = new Set<string>();
            
            const addPartAndChildren = (part: any, parentPath: string[] = []) => {
                if (processed.has(part.item)) return;
                processed.add(part.item);
                
                // Calculate missing counts for subassemblies (only if they actually have children)
                const missingCounts = (part.isSubassembly && part.children && Array.isArray(part.children) && part.children.length > 0) 
                    ? countMissingInChildren(part, allParts) 
                    : { missingMaterial: 0, missingWeight: 0 };
                
                // Get filtered children (only those with issues) for subassembly filtering
                const getFilteredChildren = (part: any, allParts: any[]): any[] => {
                    if (!part.children || !Array.isArray(part.children)) return [];
                    
                    return part.children.map((childId: string) => {
                        const child = allParts.find(p => p.item === childId);
                        return child;
                    }).filter((child: any) => child && (child.missingMaterial || 
                        ((child.mass_lb === null || child.mass_lb === undefined || child.mass_lb === "") && 
                         (child.calculatedMass === null || child.calculatedMass === undefined || child.calculatedMass === ""))));
                };
                
                const filteredChildren = part.isSubassembly ? getFilteredChildren(part, allParts) : [];
                
                // Add hierarchy metadata for display
                const enhancedPart = {
                    ...part,
                    hierarchyLevel: part.indentLevel || 0,
                    hierarchyPath: [...parentPath, part.name || part.part_name || part.item],
                    isNested: (part.indentLevel || 0) > 0,
                    parentPath: parentPath.join(' › ') || null,
                    hasSubassemblyIssues: part.hasChildrenMissingMass || false,
                    calculatedMass: part.calculatedMass,
                    isSubassembly: part.isSubassembly || false,
                    displayMass: part.calculatedMass || part.mass_lb,
                    massType: part.calculatedMass ? 'calculated' : 'direct',
                    // NEW: Missing counts and filtered children
                    missingMaterialCount: missingCounts.missingMaterial,
                    missingWeightCount: missingCounts.missingWeight,
                    filteredChildren: filteredChildren,
                    hasFilteredChildren: filteredChildren.length > 0
                };
                
                flattened.push(enhancedPart);
                
                // Add children recursively
                if (part.children && Array.isArray(part.children)) {
                    const childParts = allParts.filter((p: any) => part.children.includes(p.item));
                    childParts.forEach((child: any) => {
                        addPartAndChildren(child, enhancedPart.hierarchyPath);
                    });
                }
            };
            
            // Start with root-level parts (indentLevel 0 or no parent)
            const rootParts = parts.filter(p => (p.indentLevel || 0) === 0);
            rootParts.forEach(part => addPartAndChildren(part));
            
            // Add any orphaned parts that weren't processed
            parts.forEach(part => {
                if (!processed.has(part.item)) {
                    addPartAndChildren(part);
                }
            });
            
            return flattened;
        };

        const allFlatParts = flattenHierarchy(parts);
        const missingWeightData = allFlatParts.filter(isMissingWeight) || [];

        // Filter documents based on showOnlyMissingWeight state and part studio context
        let filteredDocuments = showOnlyMissingWeight ? missingWeightData : allFlatParts;
        
        // IMPORTANT: Only show root-level parts in the main list to fix nesting bug
        // Child parts should only appear via expansion mechanism
        filteredDocuments = filteredDocuments.filter(part => 
            (part.hierarchyLevel || part.indentLevel || 0) === 0
        );
        
        // For Part Studios, show only parts that belong to the current part studio (same elementId)
        if (isPartStudio && !showOnlyMissingWeight) {
            const currentElementId = (search as any).elementId;
            filteredDocuments = allFlatParts.filter(part => 
                part.document?.elementId === currentElementId && 
                (part.hierarchyLevel || part.indentLevel || 0) === 0
            );
        } else if (isPartStudio && showOnlyMissingWeight) {
            // When showing missing weight in part studios, still filter to current part studio
            const currentElementId = (search as any).elementId;
            filteredDocuments = missingWeightData.filter(part => 
                part.document?.elementId === currentElementId && 
                (part.hierarchyLevel || part.indentLevel || 0) === 0
            );
        }
        
        // Apply search filtering
        if (searchTerm.trim()) {
            filteredDocuments = filteredDocuments.filter(part => {
                const searchLower = searchTerm.toLowerCase();
                const partName = (part.name || part.part_name || '').toLowerCase();
                const materialName = (
                    part.material?.displayName || 
                    part.material?.name || 
                    (typeof part.material === 'string' ? part.material : '')
                ).toLowerCase();
                const itemNumber = String(part.item || '').toLowerCase();
                
                return partName.includes(searchLower) || 
                       materialName.includes(searchLower) || 
                       itemNumber.includes(searchLower);
            });
        }
        
        // Apply vendor filtering
        if (vendorFilter.trim()) {
            filteredDocuments = filteredDocuments.filter(part => 
                part.vendor && part.vendor === vendorFilter
            );
        }
        
        // Apply COTS category filtering
        const cotsCategories = (search as any).cotsCategories;
        if (cotsCategories && Array.isArray(cotsCategories) && cotsCategories.length > 0) {
            filteredDocuments = filteredDocuments.filter(part => {
                if (!part.document?.elementId) return false;
                const category = getCotsCategory(part.document.elementId);
                return category && cotsCategories.includes(category);
            });
        }
        
        // Apply comprehensive sorting with subassemblies ALWAYS first
        filteredDocuments = [...filteredDocuments].sort((a, b) => {
            // Enhanced subassembly detection for first layer
            const detectSubassembly = (doc: any) => {
                // Check explicit properties first
                if (doc.hasChildren === true || doc.isSubassembly === true) return true;
                
                // Check if this item has any child items in the breakdownMap
                const hasBreakdownItems = breakdownMap.has(doc.item) && breakdownMap.get(doc.item).length > 0;
                if (hasBreakdownItems) return true;
                
                // Check if any items in allFlatParts have this item as a parent
                // (looking for items like "1.1", "1.2" if current item is "1")
                const currentItemStr = String(doc.item || '');
                const hasChildrenInFlat = allFlatParts.some(part => {
                    const partItemStr = String(part.item || '');
                    return partItemStr.startsWith(currentItemStr + '.') && 
                           partItemStr.split('.').length === currentItemStr.split('.').length + 1;
                });
                
                return hasChildrenInFlat;
            };
            
            // FIRST PRIORITY: Subassemblies always come before individual parts
            const aIsSubassembly = detectSubassembly(a);
            const bIsSubassembly = detectSubassembly(b);
            
            if (aIsSubassembly && !bIsSubassembly) return -1;
            if (!aIsSubassembly && bIsSubassembly) return 1;
            
            // SECOND PRIORITY: Within same type (both subassemblies OR both parts), apply import/current sorting
            if (sortByImported === 'imported-first') {
                // Imported parts (not current) come first within same type
                if (!a.isCurrentDocument && b.isCurrentDocument) return -1;
                if (a.isCurrentDocument && !b.isCurrentDocument) return 1;
            } else if (sortByImported === 'current-first') {
                // Current document parts come first within same type
                if (a.isCurrentDocument && !b.isCurrentDocument) return -1;
                if (!a.isCurrentDocument && b.isCurrentDocument) return 1;
            }
            
            // THIRD PRIORITY: Within same type and same document source, sort by hierarchy level
            const aLevel = a.hierarchyLevel || a.indentLevel || 0;
            const bLevel = b.hierarchyLevel || b.indentLevel || 0;
            if (aLevel !== bLevel) return aLevel - bLevel;
            
            // FINAL PRIORITY: Within same everything, sort by item number
            const aItem = String(a.item || '');
            const bItem = String(b.item || '');
            return aItem.localeCompare(bItem, undefined, { numeric: true });
        });

        return {
            allParts,
            hasOriginCube,
            parts: allFlatParts,  // Now includes hierarchy info
            currentDocumentParts,
            importedParts,
            breakdownMap,
            weightData,
            missingWeightData,
            filteredDocuments
        };
    }, [bomData, analysis, showOnlyMissingWeight, sortByImported, isPartStudio, search, searchTerm, vendorFilter]);

    const {
        allParts,
        hasOriginCube,
        parts,
        currentDocumentParts,
        importedParts,
        weightData,
        missingWeightData,
        filteredDocuments
    } = processedData;

    // Format cache age for display
    const formatCacheAge = useCallback((ageHours: number) => {
        if (ageHours < 1) {
            return `${Math.round(ageHours * 60)} minutes ago`;
        } else if (ageHours < 24) {
            return `${Math.round(ageHours)} hours ago`;
        } else {
            const days = Math.round(ageHours / 24);
            return `${days} day${days > 1 ? "s" : ""} ago`;
        }
    }, []);

    // Handle force refresh
    const handleUpdateDocument = useCallback(async () => {
        // Prevent clicks during cooldown or if in part studio
        if (countdownSeconds > 0 || isPartStudio) {
            return;
        }

        console.log("Update button clicked - starting refresh...");
        // Start countdown immediately
        setCountdownSeconds(30);
        setIsUpdating(true);

        try {
            console.log("Refetching BOM data with forceRefresh=true...");
            console.log("Current search object:", search);

            // Set force refresh to true to trigger a fresh API call
            setForceRefresh(true);

            // Invalidate and refetch the BOM data query
            await queryClient.invalidateQueries({
                queryKey: [
                    "design-assistant",
                    "bom-data",
                    {
                        ...(search as Record<string, any>),
                        forceRefresh: true
                    }
                ],
                exact: true
            });

            console.log(
                "Query invalidated and refetched with forceRefresh=true"
            );

            // Don't reset force refresh immediately - let the user see the fresh data
            // The next time they navigate or refresh the page, it will reset naturally

            console.log("BOM data refetched, now refreshing cooldown query...");
            // Also refresh the cooldown query to get updated status
            await queryClient.refetchQueries({
                queryKey: ["design-assistant", "refresh-cooldown", search as any],
                exact: true
            });

            console.log("Update complete!");
        } catch (error) {
            console.error("Failed to update document:", error);
            // Handle rate limiting specifically
            if (
                error &&
                typeof error === "object" &&
                "status" in error &&
                error.status === 429
            ) {
                // Rate limited - refresh cooldown query to show updated countdown
                await queryClient.refetchQueries({
                    queryKey: ["design-assistant", "refresh-cooldown", search as any],
                    exact: true
                });
            }
        } finally {
            setIsUpdating(false);
        }
    }, [countdownSeconds, search, queryClient, isPartStudio]);

    // Helper function to toggle expanded state for a part
    const toggleExpanded = useCallback((itemId: string) => {
        setExpandedParts(prev => {
            const newExpanded = new Set(prev);
            if (newExpanded.has(itemId)) {
                newExpanded.delete(itemId);
            } else {
                newExpanded.add(itemId);
            }
            return newExpanded;
        });
    }, []);

    // Copy functions for debug
    const copyRawBomData = useCallback(() => {
        navigator.clipboard
            .writeText(JSON.stringify(bomData, null, 2))
            .then(() => {
                console.log("Raw BOM data copied to clipboard");
            });
    }, [bomData]);

    // Memoized callback functions to prevent unnecessary re-renders
    const handleToggleMissingWeight = useCallback(() => {
        setShowOnlyMissingWeight(!showOnlyMissingWeight);
    }, [showOnlyMissingWeight]);

    const handleToggleDebugButtons = useCallback(() => {
        setShowDebugButtons(!showDebugButtons);
    }, [showDebugButtons]);

    const handleSortByImported = useCallback(() => {
        setSortByImported(prev => {
            if (prev === 'none') return 'current-first';
            if (prev === 'current-first') return 'imported-first';
            return 'none';
        });
    }, []);

    // Early returns for different states
    if (isLoading) {
        return (
            <DesignAssistantLoading
                bomData={bomData}
                isUpdating={isUpdating}
                countdownSeconds={countdownSeconds}
                cooldownData={cooldownData}
                onUpdateDocument={handleUpdateDocument}
                formatCacheAge={formatCacheAge}
                bomDataQuery={bomDataQuery}
                isPartStudio={isPartStudio}
                analysisLoading={analysisLoading}
            />
        );
    }

    if (hasError) {
        const errorMessage =
            analysisError?.message ||
            bomDataQuery.error?.message ||
            "Unknown error";
        return (
            <DesignAssistantError
                errorMessage={errorMessage}
                analysisError={analysisError}
                bomError={bomDataQuery.error}
                bomData={bomData}
                isUpdating={isUpdating}
                countdownSeconds={countdownSeconds}
                cooldownData={cooldownData}
                onUpdateDocument={handleUpdateDocument}
                formatCacheAge={formatCacheAge}
                isPartStudio={isPartStudio}
            />
        );
    }

    if (!analysis?.documents || analysis.documents.length === 0) {
        return (
            <DesignAssistantNoParts
                bomData={bomData}
                isUpdating={isUpdating}
                countdownSeconds={countdownSeconds}
                cooldownData={cooldownData}
                onUpdateDocument={handleUpdateDocument}
                formatCacheAge={formatCacheAge}
                isPartStudio={isPartStudio}
            />
        );
    }

    return (
        <div className="design-assistant-container" style={{ padding: "20px" }}>
            <DesignAssistantHeader
                bomData={bomData}
                isUpdating={isUpdating}
                countdownSeconds={countdownSeconds}
                cooldownData={cooldownData}
                onUpdateDocument={handleUpdateDocument}
                formatCacheAge={formatCacheAge}
                isPartStudio={isPartStudio}
            />

            <DesignAssistantContent
                weightData={weightData}
                currentDocumentParts={currentDocumentParts}
                importedParts={importedParts}
                missingWeightData={missingWeightData}
                hasOriginCube={hasOriginCube}
                showOnlyMissingWeight={showOnlyMissingWeight}
                onToggleMissingWeight={handleToggleMissingWeight}
                filteredDocuments={filteredDocuments}
                expandedParts={expandedParts}
                onToggleExpanded={toggleExpanded}
                parts={parts}
                allParts={allParts}
                showDebugButtons={showDebugButtons}
                onToggleDebugButtons={handleToggleDebugButtons}
                onCopyRawBomData={copyRawBomData}
                bomData={bomData}
                sortByImported={sortByImported}
                onSortByImported={handleSortByImported}
                searchTerm={searchTerm}
                onSearchChange={setSearchTerm}
                vendorFilter={vendorFilter}
                onVendorFilterChange={setVendorFilter}
            />
        </div>
    );
}