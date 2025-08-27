import { DesignAssistantSummary } from "./design-assistant-summary";
import { DesignAssistantPartsList } from "./design-assistant-parts-list";
import { DesignAssistantDebug } from "./design-assistant-debug";

interface DesignAssistantContentProps {
    weightData: any;
    currentDocumentParts: any[];
    importedParts: any[];
    missingWeightData: any[];
    hasOriginCube: boolean;
    showOnlyMissingWeight: boolean;
    onToggleMissingWeight: () => void;
    filteredDocuments: any[];
    breakdownMap: Map<string, any[]>;
    expandedParts: Set<string>;
    onToggleExpanded: (itemId: string) => void;
    parts: any[];
    allParts?: any[]; // Add optional allParts prop for hierarchical data
    showDebugButtons: boolean;
    onToggleDebugButtons: () => void;
    onCopyRawBomData: () => void;
    bomData: any;
    sortByImported: 'none' | 'imported-first' | 'current-first';
    onSortByImported: () => void;
    searchTerm: string;
    onSearchChange: (value: string) => void;
    vendorFilter: string;
    onVendorFilterChange: (vendor: string) => void;
    documentId?: string; // Add documentId for part status loading
}

export function DesignAssistantContent({
    weightData,
    currentDocumentParts,
    importedParts,
    missingWeightData,
    hasOriginCube,
    showOnlyMissingWeight,
    onToggleMissingWeight,
    filteredDocuments,
    breakdownMap,
    expandedParts,
    onToggleExpanded,
    parts,
    allParts,
    showDebugButtons,
    onToggleDebugButtons,
    onCopyRawBomData,
    bomData,
    sortByImported,
    onSortByImported,
    searchTerm,
    onSearchChange,
    vendorFilter,
    onVendorFilterChange,
    documentId
}: DesignAssistantContentProps) {
    return (
        <>
            <DesignAssistantSummary
                weightData={weightData}
                currentDocumentParts={currentDocumentParts}
                importedParts={importedParts}
                missingWeightData={missingWeightData}
                hasOriginCube={hasOriginCube}
                showOnlyMissingWeight={showOnlyMissingWeight}
                onToggleMissingWeight={onToggleMissingWeight}
            />

            <DesignAssistantPartsList
                filteredDocuments={filteredDocuments}
                breakdownMap={breakdownMap}
                expandedParts={expandedParts}
                onToggleExpanded={onToggleExpanded}
                showOnlyMissingWeight={showOnlyMissingWeight}
                missingWeightData={missingWeightData}
                parts={parts}
                allParts={allParts}
                sortByImported={sortByImported}
                onSortByImported={onSortByImported}
                searchTerm={searchTerm}
                onSearchChange={onSearchChange}
                vendorFilter={vendorFilter}
                onVendorFilterChange={onVendorFilterChange}
                documentId={documentId}
            />

            <DesignAssistantDebug
                showDebugButtons={showDebugButtons}
                onToggleDebugButtons={onToggleDebugButtons}
                onCopyRawBomData={onCopyRawBomData}
                bomData={bomData}
                weightData={weightData}
                missingWeightData={missingWeightData}
                filteredDocuments={filteredDocuments}
            />
        </>
    );
}
