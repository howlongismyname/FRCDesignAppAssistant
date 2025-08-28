import { Button, Intent, Callout, H2 } from "@blueprintjs/core";
import { Link } from "@tanstack/react-router";

interface DesignAssistantDebugProps {
    showDebugButtons: boolean;
    onToggleDebugButtons: () => void;
    onCopyRawBomData: () => void;
    bomData: any;
    weightData: any;
    missingWeightData: any[];
    filteredDocuments: any[];
}

export function DesignAssistantDebug({
    showDebugButtons,
    onToggleDebugButtons,
    onCopyRawBomData,
    bomData,
    weightData,
    missingWeightData,
    filteredDocuments
}: DesignAssistantDebugProps) {
    if (!showDebugButtons) {
        return (
            <div style={{ marginTop: "30px", textAlign: "center" }}>
                <Button
                    small
                    intent={Intent.NONE}
                    icon="cog"
                    onClick={onToggleDebugButtons}
                >
                    Show Debug Tools
                </Button>
            </div>
        );
    }

    return (
        <>
            {/* Debug Buttons */}
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
                    intent={Intent.WARNING}
                    icon="clipboard"
                    onClick={() => {
                        console.log("=== DEBUG: Rendered Cards ===");
                        filteredDocuments.forEach((doc: any, index: number) => {
                            console.log(`Card ${index + 1}:`, {
                                item: doc.item,
                                name: doc.name,
                                partId: doc.document?.partId,
                                documentId: doc.document?.documentId,
                                elementId: doc.document?.elementId,
                                quantity: doc.quantity,
                                mass_lb: doc.mass_lb
                            });
                        });
                        console.log("=== END DEBUG ===");
                    }}
                >
                    Debug Rendered Cards
                </Button>
                <Button
                    small
                    intent={Intent.NONE}
                    icon="clipboard"
                    onClick={onCopyRawBomData}
                    style={{ marginLeft: "10px" }}
                >
                    Copy Raw BOM Data
                </Button>
                <Link to="/app/designassistant/test" search={(prev) => prev}>
                    <Button
                        small
                        intent={Intent.SUCCESS}
                        icon="lab-test"
                        style={{ marginLeft: "10px" }}
                    >
                        🧪 Test Structured Storage
                    </Button>
                </Link>
            </div>

            {/* Debug: Show document source info for first few parts */}
            <div
                style={{
                    marginBottom: "15px",
                    padding: "10px",
                    backgroundColor: "#F8F9FA",
                    borderRadius: "4px",
                    fontSize: "12px"
                }}
            >
                <strong>Document Source Debug (first 3 parts):</strong>
                {filteredDocuments
                    .slice(0, 3)
                    .map((doc: any, index: number) => (
                        <div key={index} style={{ marginTop: "5px" }}>
                            • {doc.name || doc.part_name}: isCurrentDocument ={" "}
                            {String(doc.isCurrentDocument)} (type:{" "}
                            {typeof doc.isCurrentDocument})
                        </div>
                    ))}
            </div>

            {/* BOM Debug Information */}
            {bomData && (
                <div style={{ marginTop: "30px" }}>
                    <div
                        style={{
                            display: "flex",
                            alignItems: "center",
                            gap: "15px",
                            marginBottom: "10px"
                        }}
                    >
                        <H2>BOM Debug Information</H2>
                        <Button
                            intent={Intent.SUCCESS}
                            icon="clipboard"
                            onClick={onCopyRawBomData}
                        >
                            Copy Full Debug Data
                        </Button>
                    </div>
                    <Callout
                        intent={Intent.PRIMARY}
                        title="Raw BOM Data Structure"
                    >
                        <div style={{ fontSize: "14px" }}>
                            <div>
                                <strong>Format Version:</strong>{" "}
                                {bomData.rawBomData?.formatVersion || "N/A"}
                            </div>
                            <div>
                                <strong>Total Rows:</strong>{" "}
                                {bomData.rawBomData?.totalRows || 0}
                            </div>
                            <div>
                                <strong>Deduplicated Parts:</strong>{" "}
                                {filteredDocuments.length} (assembly rows
                                removed)
                            </div>

                            <div style={{ marginTop: "15px" }}>
                                <strong>Headers:</strong>
                            </div>
                            {bomData.rawBomData?.headers?.map(
                                (header: any, index: number) => (
                                    <div
                                        key={index}
                                        style={{
                                            marginLeft: "10px",
                                            marginBottom: "5px"
                                        }}
                                    >
                                        •{" "}
                                        <strong>
                                            {header.name || "Unnamed"}:
                                        </strong>{" "}
                                        {header.id}
                                    </div>
                                )
                            )}

                            <div style={{ marginTop: "15px" }}>
                                <strong>First Row Data:</strong>
                            </div>
                            <div style={{ marginLeft: "10px" }}>
                                {bomData.rawBomData?.firstRow
                                    ?.headerIdToValue ? (
                                    Object.entries(
                                        bomData.rawBomData.firstRow
                                            .headerIdToValue
                                    ).map(
                                        ([headerId, value]: [string, any]) => (
                                            <div
                                                key={headerId}
                                                style={{
                                                    marginBottom: "3px"
                                                }}
                                            >
                                                <strong>{headerId}:</strong>{" "}
                                                {JSON.stringify(value)}
                                            </div>
                                        )
                                    )
                                ) : (
                                    <div>No headerIdToValue data found</div>
                                )}
                            </div>

                            <div style={{ marginTop: "15px" }}>
                                <strong>Item Source (First Row):</strong>
                            </div>
                            <div style={{ marginLeft: "10px" }}>
                                {bomData.rawBomData?.firstRow?.itemSource ? (
                                    Object.entries(
                                        bomData.rawBomData.firstRow.itemSource
                                    ).map(([key, value]: [string, any]) => (
                                        <div
                                            key={key}
                                            style={{
                                                marginBottom: "3px"
                                            }}
                                        >
                                            <strong>{key}:</strong>{" "}
                                            {JSON.stringify(value)}
                                        </div>
                                    ))
                                ) : (
                                    <div>No itemSource data found</div>
                                )}
                            </div>

                            <div style={{ marginTop: "15px" }}>
                                <strong>Weight Metrics:</strong>
                            </div>
                            <div style={{ marginLeft: "10px" }}>
                                <div>
                                    Total Weight: {weightData.total_weight}{" "}
                                    {weightData.unit}
                                </div>
                                <div>
                                    Unique Parts: {weightData.rows_counted}
                                </div>
                                <div>
                                    Missing Weight: {missingWeightData.length}
                                </div>
                            </div>
                        </div>
                    </Callout>
                </div>
            )}

            {/* Debug Toggle Button */}
            <div style={{ marginTop: "30px", textAlign: "center" }}>
                <Button
                    small
                    intent={Intent.NONE}
                    icon="cog"
                    onClick={onToggleDebugButtons}
                    active={showDebugButtons}
                >
                    Hide Debug Tools
                </Button>
            </div>
        </>
    );
}
