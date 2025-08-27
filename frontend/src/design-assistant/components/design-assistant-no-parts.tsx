import { H3 } from "@blueprintjs/core";
import { DesignAssistantHeader } from "./design-assistant-header";

interface DesignAssistantNoPartsProps {
    bomData: any;
    isUpdating: boolean;
    countdownSeconds: number;
    cooldownData: any;
    onUpdateDocument: () => void;
    formatCacheAge: (ageHours: number) => string;
    isPartStudio?: boolean;
}

export function DesignAssistantNoParts({
    bomData,
    isUpdating,
    countdownSeconds,
    cooldownData,
    onUpdateDocument,
    formatCacheAge,
    isPartStudio = false
}: DesignAssistantNoPartsProps) {
    return (
        <div style={{ padding: "20px" }}>
            <DesignAssistantHeader
                bomData={bomData}
                isUpdating={isUpdating}
                countdownSeconds={countdownSeconds}
                cooldownData={cooldownData}
                onUpdateDocument={onUpdateDocument}
                formatCacheAge={formatCacheAge}
                isPartStudio={isPartStudio}
            />

            <H3>No parts found to analyze!</H3>
            <p>
                This assembly doesn't contain any parts that need weight or
                material analysis.
            </p>
        </div>
    );
}
