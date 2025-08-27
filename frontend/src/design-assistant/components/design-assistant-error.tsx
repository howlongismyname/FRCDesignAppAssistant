import { Callout, Intent, H3 } from "@blueprintjs/core";
import { DesignAssistantHeader } from "./design-assistant-header";

interface DesignAssistantErrorProps {
    errorMessage: string;
    analysisError: any;
    bomError: any;
    bomData: any;
    isUpdating: boolean;
    countdownSeconds: number;
    cooldownData: any;
    onUpdateDocument: () => void;
    formatCacheAge: (ageHours: number) => string;
    isPartStudio?: boolean;
}

export function DesignAssistantError({
    errorMessage,
    analysisError,
    bomError,
    bomData,
    isUpdating,
    countdownSeconds,
    cooldownData,
    onUpdateDocument,
    formatCacheAge,
    isPartStudio = false
}: DesignAssistantErrorProps) {
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

            <Callout intent={Intent.DANGER} title="Error Details">
                <H3>Failed to analyze assembly: {errorMessage}</H3>
                {analysisError && (
                    <div>Analysis Error: {analysisError.message}</div>
                )}
                {bomError && <div>BOM Error: {bomError.message}</div>}
            </Callout>
        </div>
    );
}
