import { Button, Intent, Tag, Tooltip, InputGroup, Menu, MenuItem, Popover } from "@blueprintjs/core";
import { DesignAssistantCard } from "../design-assistant-card";
import { getCotsCategory, isCotsPart } from "../../services/cots-service";

interface DesignAssistantPartsListProps {
    filteredDocuments: any[];
    breakdownMap: Map<string, any[]>;
    expandedParts: Set<string>;
    onToggleExpanded: (itemId: string) => void;
    showOnlyMissingWeight: boolean;
    missingWeightData: any[];
    parts: any[];
    allParts?: any[]; // Add optional allParts prop for hierarchical data
    sortByImported: 'none' | 'imported-first' | 'current-first';
    onSortByImported: () => void;
    searchTerm: string;
    onSearchChange: (value: string) => void;
    vendorFilter: string;
    onVendorFilterChange: (vendor: string) => void;
}

interface NestedSubassemblyItemProps {
    item: any;
    allParts: any[];
    expandedParts: Set<string>;
    onToggleExpanded: (itemId: string) => void;
    showOnlyMissingWeight: boolean;
    isMissingWeight: (doc: any) => boolean;
    level: number;
}

// Recursive component for infinite nested subassembly support
function NestedSubassemblyItem({
    item,
    allParts,
    expandedParts,
    onToggleExpanded,
    showOnlyMissingWeight,
    isMissingWeight,
    level
}: NestedSubassemblyItemProps) {
    // Find children of this item from the flattened parts list
    const findChildren = (parentItem: string): any[] => {
        return allParts.filter(part => {
            // Check if this part is a direct child of the parent
            const partItemNum = String(part.item || '');
            const parentItemNum = String(parentItem || '');
            
            // Direct child pattern: parent "1.2" -> child "1.2.1" (exactly one more level)
            if (partItemNum.startsWith(parentItemNum + ".")) {
                const childParts = partItemNum.split('.');
                const parentParts = parentItemNum.split('.');
                return childParts.length === parentParts.length + 1;
            }
            return false;
        });
    };

    // Use explicit hasChildren property as primary determinant, fallback to calculated children
    const calculatedChildren = findChildren(item.item);
    const hasChildrenExplicit = item.hasChildren === true;
    const hasChildren = hasChildrenExplicit || calculatedChildren.length > 0;
    const children = hasChildrenExplicit ? calculatedChildren : calculatedChildren;
    const isExpanded = expandedParts.has(item.item);
    
    // Apply missing weight filter if active
    const filteredChildren = showOnlyMissingWeight 
        ? children.filter(isMissingWeight)
        : children;

    // Sort children to show subassemblies first, then individual parts
    const sortedChildren = [...filteredChildren].sort((a, b) => {
        // Use explicit hasChildren property as primary determinant
        const aHasChildren = a.hasChildren === true || findChildren(a.item).length > 0;
        const bHasChildren = b.hasChildren === true || findChildren(b.item).length > 0;
        
        // Subassemblies (items with children) come first
        if (aHasChildren && !bHasChildren) return -1;
        if (!aHasChildren && bHasChildren) return 1;
        
        // Within same type (both subassemblies or both parts), sort by item number
        const aItem = String(a.item || '');
        const bItem = String(b.item || '');
        return aItem.localeCompare(bItem, undefined, { numeric: true });
    });

    const shouldShowChildren = hasChildren && (sortedChildren.length > 0 || !showOnlyMissingWeight);
    const indentPx = level * 15; // Indent based on nesting level
    
    // Visual styling that changes based on nesting depth
    const getBorderColor = (level: number) => {
        const colors = ["#CED9E0", "#A7B6C2", "#8A9BA8", "#6D7C88"];
        return colors[Math.min(level, colors.length - 1)];
    };

    // Helper functions to count subassemblies vs individual parts for nested items
    const countSubassembliesAndPartsNested = (items: any[]) => {
        const subassemblies = items.filter(item => item.hasChildren === true || (allParts.find(p => p.item === item.item)?.isSubassembly === true)).length;
        const parts = items.filter(item => !(item.hasChildren === true || (allParts.find(p => p.item === item.item)?.isSubassembly === true))).length;
        return { subassemblies, parts };
    };

    const formatCountNested = (subassemblies: number, parts: number) => {
        const elements = [];
        if (subassemblies > 0) elements.push(`${subassemblies} ${subassemblies !== 1 ? 'subassemblies' : 'subassembly'}`);
        if (parts > 0) elements.push(`${parts} part${parts !== 1 ? 's' : ''}`);
        return elements.join(', ') || '0 items';
    };

    return (
        <div
            style={{
                marginBottom: "3px",
                marginLeft: `${indentPx}px`
            }}
        >
            {/* The card for this item */}
            <div style={{ marginBottom: hasChildren ? "5px" : "0px" }}>
                <DesignAssistantCard
                    document={{
                        id: item.document?.partId || item.document?.documentId,
                        name: item.name || item.part_name || `Part ${item.item}`,
                        thumbnail: undefined
                    }}
                    quantity={item.quantity || 1}
                    occurrenceId={item.item}
                    partId={item.document?.partId || item.document?.documentId}
                    missingMaterial={item.missingMaterial}
                    mass={item.mass_lb}
                    material={item.material}
                    documentSource={item.isCurrentDocument ? "current" : "imported"}
                    vendor={item.vendor}
                    partNumber={item.partNumber}
                    cotsCategory={item.document?.elementId ? getCotsCategory(item.document.elementId) || undefined : undefined}
                    isCots={item.document?.elementId ? isCotsPart(item.document.elementId) : false}
                    documentId={item.document?.documentId}
                    workspaceId={item.document?.workspaceId}
                    versionId={item.document?.versionId}
                    microversionId={item.document?.microversionId}
                    wvmType={item.document?.wvmType}
                    elementId={item.document?.elementId}
                />
            </div>

            {/* Show expansion button and children if this item has children */}
            {shouldShowChildren && (
                <div
                    style={{
                        marginLeft: "15px",
                        marginBottom: "5px",
                        borderLeft: `1px solid ${getBorderColor(level)}`,
                        paddingLeft: "10px"
                    }}
                >
                    <Button
                        size="small"
                        intent={Intent.PRIMARY}
                        icon={isExpanded ? "chevron-down" : "chevron-right"}
                        onClick={() => onToggleExpanded(item.item)}
                        style={{
                            padding: "3px 8px",
                            fontSize: "11px",
                            fontWeight: "500",
                            marginBottom: "3px"
                        }}
                    >
                        {isExpanded ? "Hide" : "Show"} {showOnlyMissingWeight ? "Missing Weight" : "All"} Components
                        ({(() => {
                            const counts = countSubassembliesAndPartsNested(sortedChildren);
                            return formatCountNested(counts.subassemblies, counts.parts);
                        })()})
                    </Button>

                    {/* Recursively render children */}
                    {isExpanded && (
                        <div style={{ marginTop: "5px" }}>
                            {sortedChildren.length === 0 && showOnlyMissingWeight ? (
                                <div style={{
                                    fontSize: "12px",
                                    color: "#5C7080",
                                    fontStyle: "italic",
                                    padding: "8px",
                                    textAlign: "center"
                                }}>
                                    No components missing weight in this subassembly
                                </div>
                            ) : (
                                sortedChildren.map(child => (
                                    <NestedSubassemblyItem
                                        key={`${child.item}-${child.document?.partId}`}
                                        item={child}
                                        allParts={allParts}
                                        expandedParts={expandedParts}
                                        onToggleExpanded={onToggleExpanded}
                                        showOnlyMissingWeight={showOnlyMissingWeight}
                                        isMissingWeight={isMissingWeight}
                                        level={level + 1} // Increase nesting level
                                    />
                                ))
                            )}
                        </div>
                    )}
                </div>
            )}
        </div>
    );
}

export function DesignAssistantPartsList({
    filteredDocuments,
    breakdownMap,
    expandedParts,
    onToggleExpanded,
    showOnlyMissingWeight,
    missingWeightData,
    parts,
    allParts,
    sortByImported,
    onSortByImported,
    searchTerm,
    onSearchChange,
    vendorFilter,
    onVendorFilterChange
}: DesignAssistantPartsListProps) {
    // Helper function to check if an item is missing weight (matches logic from design-assistant-home.tsx)
    const isMissingWeight = (doc: any) => {
        const mass = doc.mass_lb;
        const calculatedMass = doc.calculatedMass;
        const hasDirectMissingWeight = (mass === null || mass === undefined || mass === "") && 
                                      (calculatedMass === null || calculatedMass === undefined || calculatedMass === "");
        const hasChildrenMissingWeight = doc.hasChildrenMissingMass || false;
        
        // Only include if: direct missing weight or children have missing weight (not material issues)
        return hasDirectMissingWeight || hasChildrenMissingWeight;
    };

    // Helper functions to count subassemblies vs individual parts
    const countSubassembliesAndParts = (items: any[]) => {
        const subassemblies = items.filter(item => item.isSubassembly === true || item.hasChildren === true).length;
        const parts = items.filter(item => !(item.isSubassembly === true || item.hasChildren === true)).length;
        return { subassemblies, parts };
    };

    const formatCount = (subassemblies: number, parts: number) => {
        const elements = [];
        if (subassemblies > 0) elements.push(`${subassemblies} ${subassemblies !== 1 ? 'subassemblies' : 'subassembly'}`);
        if (parts > 0) elements.push(`${parts} part${parts !== 1 ? 's' : ''}`);
        return elements.join(', ') || '0 items';
    };

    // Get unique vendors from the parts list for filter dropdown
    const getUniqueVendors = () => {
        const vendors = new Set<string>();
        parts?.forEach((part: any) => {
            if (part.vendor && part.vendor.trim()) {
                vendors.add(part.vendor.trim());
            }
        });
        return Array.from(vendors).sort();
    };

    const uniqueVendors = getUniqueVendors();


    return (
        <>
            {/* Component Counts */}
            <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between", marginBottom: "5px" }}>
                <div style={{ display: "flex", gap: "10px", alignItems: "center" }}>
                    {(() => {
                        const counts = showOnlyMissingWeight 
                            ? countSubassembliesAndParts(missingWeightData)
                            : countSubassembliesAndParts(parts);
                        
                        return (
                            <>
                                {counts.subassemblies > 0 && (
                                    <Tag 
                                        intent={Intent.PRIMARY}
                                        style={{ fontSize: "14px", fontWeight: "600" }}
                                    >
                                        {counts.subassemblies} {counts.subassemblies !== 1 ? 'Subassemblies' : 'Subassembly'}
                                    </Tag>
                                )}
                                {counts.parts > 0 && (
                                    <Tag 
                                        intent={Intent.SUCCESS}
                                        style={{ fontSize: "14px", fontWeight: "600" }}
                                    >
                                        {counts.parts} Part{counts.parts !== 1 ? 's' : ''}
                                    </Tag>
                                )}
                                {showOnlyMissingWeight && (counts.subassemblies > 0 || counts.parts > 0) && (
                                    <Tag 
                                        intent={Intent.DANGER}
                                        style={{ fontSize: "14px", fontWeight: "600" }}
                                    >
                                        Missing Weight
                                    </Tag>
                                )}
                            </>
                        );
                    })()}
                </div>
                
                {/* Search Bar */}
                <div style={{ flex: "1", maxWidth: "300px", margin: "0 15px" }}>
                    <InputGroup
                        leftIcon="search"
                        placeholder="Search parts, materials, or item numbers..."
                        value={searchTerm}
                        onChange={(e) => onSearchChange(e.target.value)}
                        rightElement={searchTerm ? (
                            <Button
                                icon="cross"
                                minimal
                                small
                                onClick={() => onSearchChange('')}
                            />
                        ) : undefined}
                    />
                </div>
                
                {/* Sort Button */}
                <Button
                    size="small"
                    intent={sortByImported !== 'none' ? Intent.PRIMARY : Intent.NONE}
                    icon={sortByImported === 'current-first' ? "sort-asc" : sortByImported === 'imported-first' ? "sort-desc" : "sort"}
                    onClick={onSortByImported}
                    style={{ minWidth: "120px" }}
                >
                    {sortByImported === 'none' && "Sort by Source"}
                    {sortByImported === 'current-first' && "Current First"}
                    {sortByImported === 'imported-first' && "Imported First"}
                </Button>
                
                {/* Vendor Filter Button */}
                {uniqueVendors.length > 0 && (
                    <Popover
                        content={
                            <Menu>
                                <MenuItem
                                    text="All Vendors"
                                    icon={vendorFilter === '' ? "tick" : "blank"}
                                    onClick={() => onVendorFilterChange('')}
                                />
                                {uniqueVendors.map((vendor) => (
                                    <MenuItem
                                        key={vendor}
                                        text={vendor}
                                        icon={vendorFilter === vendor ? "tick" : "blank"}
                                        onClick={() => onVendorFilterChange(vendor)}
                                    />
                                ))}
                            </Menu>
                        }
                        placement="bottom-end"
                    >
                        <Button
                            size="small"
                            intent={vendorFilter ? Intent.PRIMARY : Intent.NONE}
                            icon="filter"
                            rightIcon="caret-down"
                            style={{ minWidth: "120px", marginLeft: "10px" }}
                        >
                            {vendorFilter || "All Vendors"}
                        </Button>
                    </Popover>
                )}
            </div>

            {/* Enhanced Parts List with Hierarchy */}
            <div
                style={{
                    marginTop: "5px",
                    maxHeight: "65vh",
                    overflowY: "auto",
                    border: "1px solid #E1E8ED",
                    borderRadius: "3px",
                    padding: "5px"
                }}
            >
                {filteredDocuments.map((doc: any) => {
                    const hasBreakdown = breakdownMap.has(doc.item);
                    const isExpanded = expandedParts.has(doc.item);
                    const breakdownItems = breakdownMap.get(doc.item) || [];
                    
                    // Calculate indentation for hierarchy
                    const indentLevel = doc.hierarchyLevel || 0;
                    const indentPx = indentLevel * 15; // Reduced from 20px
                    
                    // Determine mass display
                    const displayMass = doc.displayMass || doc.mass_lb;
                    const massType = doc.massType || 'direct';
                    
                    // Enhanced styling for hierarchy levels - more compact
                    const hierarchyStyle = {
                        marginLeft: `${indentPx}px`,
                        borderLeft: indentLevel > 0 ? "1px solid #CED9E0" : "none",
                        paddingLeft: indentLevel > 0 ? "8px" : "0px",
                        marginBottom: "3px", // Reduced spacing
                        position: "relative" as const
                    };

                    return (
                        <div
                            key={`${doc.item}-${
                                doc.document?.partId || doc.document?.documentId
                            }-${doc.document?.elementId}`}
                            style={hierarchyStyle}
                        >
                            {/* Hierarchy indicator line */}
                            {indentLevel > 0 && (
                                <div
                                    style={{
                                        position: "absolute",
                                        left: "-1px",
                                        top: "0",
                                        bottom: "0",
                                        width: "1px",
                                        background: "linear-gradient(to bottom, #CED9E0 50%, transparent 50%)",
                                        backgroundSize: "1px 6px"
                                    }}
                                />
                            )}
                            
                            {/* Enhanced Card with Tags */}
                            <div style={{ position: "relative" }}>
                                {/* Hierarchy and Status Tags - more compact */}
                                <div style={{ marginBottom: "3px", display: "flex", gap: "3px", flexWrap: "wrap" }}>
                                    {/* Subassembly tag - enhanced detection for first layer */}
                                    {(() => {
                                        // Enhanced subassembly detection
                                        if (doc.hasChildren === true || doc.isSubassembly === true) return true;
                                        if (hasBreakdown && breakdownItems.length > 0) return true;
                                        
                                        // Check if this item has children in the parts list
                                        const currentItemStr = String(doc.item || '');
                                        const hasChildrenInParts = parts.some((part: any) => {
                                            const partItemStr = String(part.item || '');
                                            return partItemStr.startsWith(currentItemStr + '.') && 
                                                   partItemStr.split('.').length === currentItemStr.split('.').length + 1;
                                        });
                                        
                                        return hasChildrenInParts;
                                    })() && (
                                        <Tag 
                                            intent={Intent.PRIMARY} 
                                            minimal
                                            icon="folder-close"
                                        >
                                            Subassembly
                                        </Tag>
                                    )}
                                    
                                    {/* Hierarchy path tag for nested items */}
                                    {doc.parentPath && (
                                        <Tooltip content={`Hierarchy: ${doc.parentPath}`}>
                                            <Tag 
                                                intent={Intent.NONE} 
                                                minimal
                                                icon="diagram-tree"
                                            >
                                                {doc.parentPath.split(' › ').pop()}
                                            </Tag>
                                        </Tooltip>
                                    )}
                                    
                                    {/* Mass calculation indicator */}
                                    {massType === 'calculated' && (
                                        <Tooltip content={`Mass calculated from ${doc.children?.length || 0} components`}>
                                            <Tag 
                                                intent={Intent.SUCCESS} 
                                                minimal
                                                icon="calculator"
                                            >
                                                Calculated
                                            </Tag>
                                        </Tooltip>
                                    )}
                                    
                                    {/* Missing material count tag - only show for subassemblies with valid children */}
                                    {doc.isSubassembly && doc.missingMaterialCount > 0 && (doc.children?.length > 0 || doc.hasFilteredChildren) && (
                                        <Tooltip content={`${doc.missingMaterialCount} component(s) missing materials`}>
                                            <Tag 
                                                intent={Intent.WARNING} 
                                                minimal
                                                icon="warning-sign"
                                            >
                                                Missing Materials: {doc.missingMaterialCount}
                                            </Tag>
                                        </Tooltip>
                                    )}
                                    
                                    {/* Missing weight count tag - only show for subassemblies with valid children */}
                                    {doc.isSubassembly && doc.missingWeightCount > 0 && (doc.children?.length > 0 || doc.hasFilteredChildren) && (
                                        <Tooltip content={`${doc.missingWeightCount} component(s) missing weight/mass`}>
                                            <Tag 
                                                intent={Intent.DANGER} 
                                                minimal
                                                icon="error"
                                            >
                                                Missing Weight: {doc.missingWeightCount}
                                            </Tag>
                                        </Tooltip>
                                    )}
                                </div>
                                
                                <DesignAssistantCard
                                    document={{
                                        id:
                                            doc.document?.partId ||
                                            doc.document?.documentId,
                                        name:
                                            doc.name ||
                                            doc.part_name ||
                                            `Part ${
                                                doc.document?.partId ||
                                                doc.document?.documentId
                                            }`,
                                        thumbnail: undefined
                                    }}
                                    quantity={doc.quantity || 1}
                                    occurrenceId={doc.item}
                                    partId={
                                        doc.document?.partId ||
                                        doc.document?.documentId
                                    }
                                    missingMaterial={doc.missingMaterial}
                                    mass={displayMass}
                                    material={doc.material}
                                    documentSource={
                                        doc.isCurrentDocument
                                            ? "current"
                                            : "imported"
                                    }
                                    vendor={doc.vendor}
                                    partNumber={doc.partNumber}
                                    cotsCategory={doc.document?.elementId ? getCotsCategory(doc.document.elementId) || undefined : undefined}
                                    isCots={doc.document?.elementId ? isCotsPart(doc.document.elementId) : false}
                                    documentId={doc.document?.documentId}
                                    workspaceId={doc.document?.workspaceId}
                                    versionId={doc.document?.versionId}
                                    microversionId={doc.document?.microversionId}
                                    wvmType={doc.document?.wvmType}
                                    elementId={doc.document?.elementId}
                                />
                            </div>

                            {/* Enhanced breakdown with filtered children for subassemblies */}
                            {(hasBreakdown || (doc.isSubassembly && doc.hasFilteredChildren)) && (
                                <div
                                    style={{
                                        marginLeft: "15px",
                                        marginBottom: "5px",
                                        borderLeft: "1px solid #CED9E0",
                                        paddingLeft: "10px"
                                    }}
                                >
                                    {/* Show breakdown button (legacy support) */}
                                    {hasBreakdown && (
                                        showOnlyMissingWeight 
                                            ? breakdownItems.filter(isMissingWeight).length > 0
                                            : true
                                    ) && (
                                        <Button
                                            size="small"
                                            intent={Intent.PRIMARY}
                                            icon={
                                                isExpanded
                                                    ? "chevron-down"
                                                    : "chevron-right"
                                            }
                                            onClick={() =>
                                                onToggleExpanded(doc.item)
                                            }
                                            style={{
                                                padding: "3px 8px",
                                                fontSize: "11px",
                                                fontWeight: "500",
                                                marginBottom: "3px",
                                                marginRight: "5px"
                                            }}
                                        >
                                            {isExpanded ? "Hide" : "Show"} {showOnlyMissingWeight ? "Missing Weight" : "All"} Components
                                            ({(() => {
                                                const items = showOnlyMissingWeight ? breakdownItems.filter(isMissingWeight) : breakdownItems;
                                                const counts = countSubassembliesAndParts(items);
                                                return formatCount(counts.subassemblies, counts.parts);
                                            })()})
                                        </Button>
                                    )}
                                    

                                    {/* Show all breakdown items */}
                                    {isExpanded && hasBreakdown && (
                                        showOnlyMissingWeight 
                                            ? breakdownItems.filter(isMissingWeight).length > 0
                                            : true
                                    ) && (
                                        <div
                                            style={{
                                                marginTop: "5px",
                                                paddingLeft: "5px"
                                            }}
                                        >
                                            {(() => {
                                                const filteredBreakdownItems = showOnlyMissingWeight 
                                                    ? breakdownItems.filter(isMissingWeight)
                                                    : breakdownItems;
                                                
                                                if (filteredBreakdownItems.length === 0 && showOnlyMissingWeight) {
                                                    return (
                                                        <div style={{
                                                            fontSize: "12px",
                                                            color: "#5C7080",
                                                            fontStyle: "italic",
                                                            padding: "8px",
                                                            textAlign: "center"
                                                        }}>
                                                            No components missing weight in this subassembly
                                                        </div>
                                                    );
                                                }
                                                
                                                return filteredBreakdownItems.map(
                                                    (breakdownItem: any) => (
                                                        <NestedSubassemblyItem
                                                            key={`${breakdownItem.item}-${breakdownItem.document?.partId}`}
                                                            item={breakdownItem}
                                                            allParts={allParts || parts}
                                                            expandedParts={expandedParts}
                                                            onToggleExpanded={onToggleExpanded}
                                                            showOnlyMissingWeight={showOnlyMissingWeight}
                                                            isMissingWeight={isMissingWeight}
                                                            level={1} // Start at level 1 for first nested items
                                                        />
                                                    )
                                                );
                                            })()}
                                        </div>
                                    )}
                                    
                                </div>
                            )}
                        </div>
                    );
                })}
            </div>
        </>
    );
}
