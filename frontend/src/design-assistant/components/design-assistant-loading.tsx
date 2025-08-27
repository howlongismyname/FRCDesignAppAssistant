import { Spinner, H3, ProgressBar, Intent } from "@blueprintjs/core";
import { DesignAssistantHeader } from "./design-assistant-header";

interface DesignAssistantLoadingProps {
    bomData: any;
    isUpdating: boolean;
    countdownSeconds: number;
    cooldownData: any;
    onUpdateDocument: () => void;
    formatCacheAge: (ageHours: number) => string;
    bomDataQuery: any;
    isPartStudio?: boolean;
    analysisLoading?: boolean;
}

export function DesignAssistantLoading({
    bomData,
    isUpdating,
    countdownSeconds,
    cooldownData,
    onUpdateDocument,
    formatCacheAge,
    bomDataQuery,
    isPartStudio = false,
    analysisLoading = false
}: DesignAssistantLoadingProps) {
    // Determine current loading phase and progress
    const getCurrentLoadingState = () => {
        if (bomDataQuery.isLoading) {
            return {
                progress: 0.25,
                status: "Fetching BOM data from Onshape...",
                intent: Intent.PRIMARY as Intent
            };
        } else if (bomData && !bomDataQuery.isLoading && analysisLoading) {
            return {
                progress: 0.65,
                status: "Processing assembly hierarchy and calculating masses...",
                intent: Intent.PRIMARY as Intent
            };
        } else if (bomData && !bomDataQuery.isLoading && !analysisLoading) {
            return {
                progress: 0.95,
                status: "Finalizing analysis results...",
                intent: Intent.SUCCESS as Intent
            };
        } else {
            return {
                progress: 0.1,
                status: "Initializing analysis...",
                intent: Intent.NONE as Intent
            };
        }
    };

    const loadingState = getCurrentLoadingState();

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

            {/* Enhanced loading state with progress bar */}
            <div style={{ textAlign: "center", padding: "40px 0", maxWidth: "600px", margin: "0 auto" }}>
                <Spinner size={50} />
                
                <H3 style={{ marginTop: "20px", marginBottom: "30px" }}>
                    {loadingState.status}
                </H3>

                {/* Progress bar */}
                <div style={{ marginBottom: "20px" }}>
                    <ProgressBar
                        value={loadingState.progress}
                        intent={loadingState.intent}
                        animate={true}
                        stripes={true}
                    />
                    <div style={{ 
                        fontSize: "12px", 
                        color: "#5C7080", 
                        textAlign: "right", 
                        marginTop: "4px" 
                    }}>
                        {Math.round(loadingState.progress * 100)}% complete
                    </div>
                </div>

                {/* Detailed status steps */}
                <div style={{ textAlign: "left", fontSize: "14px", color: "#5C7080" }}>
                    <div style={{ display: "flex", alignItems: "center", marginBottom: "8px" }}>
                        <span style={{ marginRight: "8px" }}>
                            {bomDataQuery.isLoading ? "⏳" : "✅"}
                        </span>
                        <span style={{ color: bomDataQuery.isLoading ? "#137CBD" : "#0D8050" }}>
                            Loading assembly data from Onshape
                        </span>
                    </div>
                    
                    <div style={{ display: "flex", alignItems: "center", marginBottom: "8px" }}>
                        <span style={{ marginRight: "8px" }}>
                            {bomDataQuery.isLoading ? "⏸️" : analysisLoading ? "⏳" : bomData ? "✅" : "⏸️"}
                        </span>
                        <span style={{ color: bomData && !bomDataQuery.isLoading && analysisLoading ? "#137CBD" : bomData && !analysisLoading ? "#0D8050" : "#5C7080" }}>
                            Processing hierarchical structure
                        </span>
                    </div>
                    
                    <div style={{ display: "flex", alignItems: "center", marginBottom: "8px" }}>
                        <span style={{ marginRight: "8px" }}>
                            {bomDataQuery.isLoading ? "⏸️" : analysisLoading ? "⏳" : bomData ? "✅" : "⏸️"}
                        </span>
                        <span style={{ color: bomData && !bomDataQuery.isLoading && analysisLoading ? "#137CBD" : bomData && !analysisLoading ? "#0D8050" : "#5C7080" }}>
                            Calculating subassembly masses
                        </span>
                    </div>
                    
                    <div style={{ display: "flex", alignItems: "center" }}>
                        <span style={{ marginRight: "8px" }}>
                            {bomDataQuery.isLoading || analysisLoading ? "⏸️" : bomData ? "✅" : "⏸️"}
                        </span>
                        <span style={{ color: bomData && !analysisLoading ? "#0D8050" : "#5C7080" }}>
                            Analyzing missing materials and weights
                        </span>
                    </div>
                </div>
            </div>
        </div>
    );
}
