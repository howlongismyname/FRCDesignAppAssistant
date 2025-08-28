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
    // Assembly/subassembly detection properties
    hasChildren?: boolean;
    isSubassembly?: boolean;
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
        hasChildren,
        isSubassembly,
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

    // Create Onshape URL and open in new tab
    const openOnshapeLink = useCallback(() => {
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

        // Open in new tab
        window.open(onshapeUrl, '_blank', 'noopener,noreferrer');
        console.log("Opened Onshape link in new tab:", onshapeUrl);
    }, [
        documentId,
        workspaceId,
        versionId,
        microversionId,
        wvmType,
        elementId
    ]);

    // Check if we have all required data for the open link button
    const canOpenLink =
        documentId &&
        elementId &&
        ((wvmType === "w" && workspaceId) ||
            (wvmType === "v" && versionId) ||
            (wvmType === "m" && microversionId) ||
            workspaceId); // Fallback for parts without explicit wvmType

    // Check if this is a subassembly/assembly (has children)
    const isAssemblyOrSubassembly = hasChildren === true || isSubassembly === true;


    return (
        <Card
            className="item-card"
            compact
            style={{
                margin: 0,
                borderRadius: 0,
                borderTop: "none",
                borderLeft: isAssemblyOrSubassembly ? "4px solid #137CBD" : "none", // Blue bar for assemblies/subassemblies
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
                        justifyContent: "space-between",
                        marginBottom: "2px"
                    }}
                >
                    <EntityTitle 
                        title={
                            <Text 
                                style={{ 
                                    fontSize: "16px", 
                                    fontWeight: "600",
                                    lineHeight: "1.3"
                                }}
                            >
                                {document.name}
                            </Text>
                        } 
                    />
                    <div
                        style={{
                            fontSize: "10px",
                            opacity: 0.6,
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
                        <Tag minimal intent={Intent.NONE}>Qty: {quantity}</Tag>
                    </Tooltip>

                    <Tooltip
                        content={
                            mass
                                ? `Precise value: ${mass} lbs`
                                : "No mass data available"
                        }
                    >
                        <Tag minimal intent={!mass ? Intent.DANGER : Intent.NONE}>
                            Mass: {mass ? `${mass.toFixed(2)} lbs` : "Unknown"}
                        </Tag>
                    </Tooltip>

                    {/* Only show material box for individual parts, not assemblies/subassemblies */}
                    {!isAssemblyOrSubassembly && (
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
                            <Tag minimal intent={!mass ? Intent.DANGER : (material ? Intent.NONE : Intent.WARNING)}>
                                {!mass
                                    ? "No Weight"
                                    : material?.displayName ||
                                      material?.name ||
                                      (typeof material === "string"
                                          ? material
                                          : "Unknown Material")}
                            </Tag>
                        </Tooltip>
                    )}

                    {documentSource === "imported" && !isCots && (
                        <Tag minimal intent={Intent.NONE} icon="import">
                            Imported
                        </Tag>
                    )}

                    {/* Generic part name indicator */}
                    {isGenericPartName(document.name) && (
                        <Tooltip content="This part has a generic name like 'Part 1'. Consider giving it a more descriptive name in Onshape.">
                            <Tag minimal intent={Intent.NONE} icon="warning-sign">
                                Not Named
                            </Tag>
                        </Tooltip>
                    )}

                    {/* Vendor tag */}
                    {vendor && (
                        <Tooltip content={`Vendor: ${vendor}`}>
                            <Tag minimal intent={Intent.NONE} icon="shop">
                                {vendor}
                            </Tag>
                        </Tooltip>
                    )}

                    {/* Part Number tag */}
                    {partNumber && (
                        <Tooltip content={`Part Number: ${partNumber}`}>
                            <Tag minimal intent={Intent.NONE} icon="barcode">
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
                            <Tag minimal intent={Intent.NONE} icon="book">
                                FRCDesignLib
                            </Tag>
                        </Tooltip>
                    )}

                    {/* Open Onshape Link button */}
                    {canOpenLink && (
                        <Tooltip content="Open in Onshape in a new tab">
                            <Button
                                size="small"
                                icon="share"
                                intent={Intent.NONE}
                                onClick={openOnshapeLink}
                                style={{ opacity: 0.7, background: 'transparent', border: 'none' }}
                            >
                                Open Link
                            </Button>
                        </Tooltip>
                    )}

                </div>
            </div>
        </Card>
    );
}
