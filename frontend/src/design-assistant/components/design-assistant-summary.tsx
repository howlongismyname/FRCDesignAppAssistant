import { Tag, Intent, Button } from "@blueprintjs/core";

interface DesignAssistantSummaryProps {
    weightData: any;
    currentDocumentParts: any[];
    importedParts: any[];
    missingWeightData: any[];
    hasOriginCube: boolean;
    showOnlyMissingWeight: boolean;
    onToggleMissingWeight: () => void;
}

export function DesignAssistantSummary({
    weightData,
    currentDocumentParts,
    importedParts,
    missingWeightData,
    hasOriginCube,
    showOnlyMissingWeight,
    onToggleMissingWeight
}: DesignAssistantSummaryProps) {
    return (
        <>
            <div
                style={{
                    fontSize: "12px",
                    color: "#666",
                    marginBottom: "10px"
                }}
            >
                Note: BOM weights are aggregated from individual part weights.
                Breakdown items (like 15.1, 15.2) are hidden but accessible via
                dropdown.
            </div>

            {/* Origin Cube Checker */}
            <div style={{ marginBottom: "15px" }}>
                <Tag
                    intent={hasOriginCube ? Intent.SUCCESS : Intent.WARNING}
                    icon={hasOriginCube ? "tick" : "cross"}
                    minimal
                >
                    Origin Cube: {hasOriginCube ? "Present" : "Not Found"}
                </Tag>
            </div>

            {/* Weight Metrics Summary */}
            {weightData && (
                <div
                    style={{
                        marginBottom: "15px",
                        display: "flex",
                        alignItems: "center",
                        gap: "10px",
                        flexWrap: "wrap"
                    }}
                >
                    <Tag
                        intent={Intent.PRIMARY}
                        title={`${weightData.total_weight} ${weightData.unit}`}
                    >
                        Total: {weightData.total_weight.toFixed(2)}{" "}
                        {weightData.unit}
                    </Tag>
                    <Tag intent={Intent.SUCCESS}>
                        Current Document: {currentDocumentParts.length}
                    </Tag>
                    <Tag intent={Intent.WARNING}>
                        Imported: {importedParts.length}
                    </Tag>
                    <Tag intent={Intent.DANGER}>
                        Missing Weight: {missingWeightData.length}
                    </Tag>
                </div>
            )}

            {/* Filter Controls */}
            <div
                style={{
                    marginBottom: "15px",
                    display: "flex",
                    alignItems: "center",
                    gap: "10px",
                    flexWrap: "wrap"
                }}
            >
                <Button
                    small
                    intent={
                        showOnlyMissingWeight ? Intent.PRIMARY : Intent.DANGER
                    }
                    onClick={onToggleMissingWeight}
                    active={showOnlyMissingWeight}
                >
                    {showOnlyMissingWeight ? "Show All" : "Show Missing Weight"}
                </Button>
            </div>
        </>
    );
}
