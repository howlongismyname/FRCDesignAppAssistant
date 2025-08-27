import {
    Card,
    EntityTitle,
    Text,
    Tag,
    Intent,
    Button,
    Tooltip
} from "@blueprintjs/core";
import { ReactNode, useCallback } from "react";

interface DesignAssistantCardProps {
    document: {
        id: string;
        name: string;
        thumbnail?: string;
    };
    quantity: number;
    occurrenceId: string;
    partId: string;
    missingMaterial: boolean;
    mass?: number;
    material?: any;
    documentSource?: "current" | "imported";
    vendor?: string;
    partNumber?: string;
    cotsCategory?: string;
    isCots?: boolean;
    // Onshape link properties
    documentId?: string;
    workspaceId?: string;
    versionId?: string;
    microversionId?: string;
    wvmType?: string;
    elementId?: string;
}

export function DesignAssistantCard(
    props: DesignAssistantCardProps
): ReactNode {
    const {
        document,
        quantity,
        occurrenceId,
        mass,
        material,
        documentSource,
        vendor,
        partNumber,
        cotsCategory,
        isCots,
        documentId,
        workspaceId,
        versionId,
        microversionId,
        wvmType,
        elementId
    } = props;

    // Function to detect generic part names
    const isGenericPartName = useCallback((name: string) => {
        if (!name) return false;

        // Check for patterns like "Part 1", "Part 2", "part 3", etc.
        // Also check for variations like "Part1", "Part_1", etc.
        const genericPatterns = [
            /^part\s*\d+$/i, // "Part 1", "Part 2", etc.
            /^part\s*_\s*\d+$/i, // "Part_1", "Part _ 2", etc.
            /^part\d+$/i, // "Part1", "Part2", etc.
            /^part_\d+$/i // "Part_1", "Part_2", etc.
        ];

        return genericPatterns.some((pattern) => pattern.test(name.trim()));
    }, []);

    // Create Onshape URL and copy to clipboard
    const copyOnshapeLink = useCallback(() => {
        if (!documentId || !elementId) {
            console.warn("Missing required IDs for Onshape link:", {
                documentId,
                elementId
            });
            return;
        }

        let onshapeUrl: string;

        // Determine URL format based on wvmType
        if (wvmType === "w" && workspaceId) {
            // Workspace URL (editable)
            onshapeUrl = `https://cad.onshape.com/documents/${documentId}/w/${workspaceId}/e/${elementId}`;
        } else if (wvmType === "v" && versionId) {
            // Version URL (read-only)
            onshapeUrl = `https://cad.onshape.com/documents/${documentId}/v/${versionId}/e/${elementId}`;
        } else if (wvmType === "m" && microversionId) {
            // Microversion URL (specific snapshot)
            onshapeUrl = `https://cad.onshape.com/documents/${documentId}/m/${microversionId}/e/${elementId}`;
        } else if (workspaceId) {
            // Fallback to workspace if available
            onshapeUrl = `https://cad.onshape.com/documents/${documentId}/w/${workspaceId}/e/${elementId}`;
        } else {
            console.warn("Cannot determine appropriate Onshape URL format", {
                wvmType,
                workspaceId,
                versionId,
                microversionId
            });
            return;
        }

        navigator.clipboard
            .writeText(onshapeUrl)
            .then(() => {
                console.log("Onshape link copied to clipboard:", onshapeUrl);
            })
            .catch((err) => {
                console.error("Failed to copy link to clipboard:", err);
            });
    }, [
        documentId,
        workspaceId,
        versionId,
        microversionId,
        wvmType,
        elementId
    ]);

    // Check if we have all required data for the copy link button
    const canCopyLink =
        documentId &&
        elementId &&
        ((wvmType === "w" && workspaceId) ||
            (wvmType === "v" && versionId) ||
            (wvmType === "m" && microversionId) ||
            workspaceId); // Fallback for parts without explicit wvmType


    return (
        <Card
            className="item-card"
            compact
            style={{
                margin: 0,
                borderRadius: 0,
                borderTop: "none",
                borderLeft: "none",
                borderRight: "none",
                maxWidth: "100%",
                width: "auto"
            }}
        >
            <div
                style={{ display: "flex", flexDirection: "column", gap: "4px" }}
            >
                <div
                    style={{
                        display: "flex",
                        alignItems: "center",
                        justifyContent: "space-between"
                    }}
                >
                    <EntityTitle title={<Text>{document.name}</Text>} />
                    <div
                        style={{
                            fontSize: "11px",
                            color: "#667",
                            flexShrink: 0
                        }}
                    >
                        ID: {occurrenceId}
                    </div>
                </div>

                <div
                    style={{
                        display: "flex",
                        alignItems: "center",
                        gap: "6px"
                    }}
                >
                    <Tooltip
                        content={`Total mass for this quantity: ${
                            mass && quantity
                                ? (mass * quantity).toFixed(4)
                                : "Unknown"
                        } lbs`}
                    >
                        <Tag intent={Intent.PRIMARY}>Qty: {quantity}</Tag>
                    </Tooltip>

                    <Tooltip
                        content={
                            mass
                                ? `Precise value: ${mass} lbs`
                                : "No mass data available"
                        }
                    >
                        <Tag intent={Intent.WARNING}>
                            Mass: {mass ? `${mass.toFixed(2)} lbs` : "Unknown"}
                        </Tag>
                    </Tooltip>

                    <Tooltip
                        content={
                            !mass
                                ? "No weight data available for this part"
                                : `Material: ${
                                      material?.displayName ||
                                      material?.name ||
                                      (typeof material === "string"
                                          ? material
                                          : "Unknown Material")
                                  }${
                                      material?.density
                                          ? ` | Density: ${material.density}`
                                          : ""
                                  }${
                                      material?.type
                                          ? ` | Type: ${material.type}`
                                          : ""
                                  }`
                        }
                    >
                        <Tag intent={!mass ? Intent.DANGER : Intent.SUCCESS}>
                            {!mass
                                ? "No Weight"
                                : material?.displayName ||
                                  material?.name ||
                                  (typeof material === "string"
                                      ? material
                                      : "Unknown Material")}
                        </Tag>
                    </Tooltip>

                    {documentSource === "imported" && !isCots && (
                        <Tag intent={Intent.NONE} icon="import">
                            Imported
                        </Tag>
                    )}

                    {/* Generic part name indicator */}
                    {isGenericPartName(document.name) && (
                        <Tooltip content="This part has a generic name like 'Part 1'. Consider giving it a more descriptive name in Onshape.">
                            <Tag intent={Intent.WARNING} icon="warning-sign">
                                Not Named
                            </Tag>
                        </Tooltip>
                    )}

                    {/* Vendor tag */}
                    {vendor && (
                        <Tooltip content={`Vendor: ${vendor}`}>
                            <Tag intent={Intent.NONE} icon="shop">
                                {vendor}
                            </Tag>
                        </Tooltip>
                    )}

                    {/* Part Number tag */}
                    {partNumber && (
                        <Tooltip content={`Part Number: ${partNumber}`}>
                            <Tag intent={Intent.NONE} icon="barcode">
                                {partNumber}
                            </Tag>
                        </Tooltip>
                    )}

                    {/* FRCDesignLib tag */}
                    {isCots && (
                        <Tooltip
                            content={
                                cotsCategory
                                    ? `FRCDesignLib Category: ${cotsCategory}`
                                    : "Component from FRC Design Library with verified specifications"
                            }
                        >
                            <Tag intent={Intent.SUCCESS} icon="book">
                                FRCDesignLib
                            </Tag>
                        </Tooltip>
                    )}

                    {/* Copy Onshape Link button */}
                    {canCopyLink && (
                        <Tooltip content="Copy Onshape link to clipboard">
                            <Button
                                size="small"
                                minimal
                                icon="clipboard"
                                intent={Intent.PRIMARY}
                                onClick={copyOnshapeLink}
                            >
                                Copy Link
                            </Button>
                        </Tooltip>
                    )}

                </div>
            </div>
        </Card>
    );
}
