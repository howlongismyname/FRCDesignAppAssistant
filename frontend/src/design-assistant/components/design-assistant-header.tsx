import { H1, H2, Callout, Intent } from "@blueprintjs/core";
import { DesignAssistantCacheInfo } from "./design-assistant-cache-info";

interface DesignAssistantHeaderProps {
    bomData: any;
    isUpdating: boolean;
    countdownSeconds: number;
    cooldownData: any;
    onUpdateDocument: () => void;
    formatCacheAge: (ageHours: number) => string;
    isPartStudio?: boolean;
}

export function DesignAssistantHeader({
    bomData,
    isUpdating,
    countdownSeconds,
    cooldownData,
    onUpdateDocument,
    formatCacheAge,
    isPartStudio = false
}: DesignAssistantHeaderProps) {
    return (
        <>
            <H1>Design Assistant</H1>
            
            {/* Part Studio Context Banner */}
            {isPartStudio && (
                <Callout
                    intent={Intent.WARNING}
                    icon="info-sign"
                    title="Part Studio Context"
                    style={{ marginBottom: "15px" }}
                >
                    You are viewing assembly data from within a Part Studio. 
                    This view shows parts from the parent assembly but cannot be updated from here.
                </Callout>
            )}
            
            <H2>{isPartStudio ? "Assembly Parts (Part Studio View)" : "Assembly Analysis Results"}</H2>

            {/* Cache Information and Update Button - Hide update for Part Studios */}
            {bomData?.cacheInfo && !isPartStudio && (
                <DesignAssistantCacheInfo
                    cacheInfo={bomData.cacheInfo}
                    isUpdating={isUpdating}
                    countdownSeconds={countdownSeconds}
                    cooldownData={cooldownData}
                    onUpdateDocument={onUpdateDocument}
                    formatCacheAge={formatCacheAge}
                />
            )}
            
            {/* Show cache info without update button for Part Studios */}
            {bomData?.cacheInfo && isPartStudio && (
                <div style={{ marginBottom: "15px", fontSize: "14px", color: "#5C7080" }}>
                    Assembly data cached {formatCacheAge(bomData.cacheInfo.ageHours)}
                    {bomData.cacheInfo.isCached ? " (from cache)" : " (fresh)"}
                </div>
            )}
        </>
    );
}
