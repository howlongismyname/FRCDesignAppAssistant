import { Button, Intent, Tag } from "@blueprintjs/core";

interface DesignAssistantCacheInfoProps {
    cacheInfo: {
        isCached: boolean;
        lastUpdated: string;
        ageHours: number | null;
    };
    isUpdating: boolean;
    countdownSeconds: number;
    cooldownData: any;
    onUpdateDocument: () => void;
    formatCacheAge: (ageHours: number) => string;
}

export function DesignAssistantCacheInfo({
    cacheInfo,
    isUpdating,
    countdownSeconds,
    cooldownData,
    onUpdateDocument,
    formatCacheAge
}: DesignAssistantCacheInfoProps) {
    return (
        <div
            style={{
                display: "flex",
                alignItems: "center",
                justifyContent: "space-between",
                flexWrap: "wrap",
                gap: "10px",
                marginBottom: "20px"
            }}
        >
            <div style={{ display: "flex", gap: "10px", alignItems: "center", flexWrap: "wrap" }}>
                <Tag 
                    intent={cacheInfo.isCached ? Intent.PRIMARY : Intent.SUCCESS}
                    style={{ 
                        fontSize: "14px", 
                        fontWeight: "600",
                        color: "white"
                    }}
                >
                    {cacheInfo.isCached ? "Cached Data" : "Fresh Data"}
                </Tag>
                {cacheInfo.isCached && cacheInfo.ageHours !== null && (
                    <span
                        style={{
                            color: "var(--bp-text-color-muted)",
                            fontSize: "13px"
                        }}
                    >
                        Updated {formatCacheAge(cacheInfo.ageHours)}
                    </span>
                )}
            </div>
            <div style={{ flexShrink: 0 }}>
                <Button
                    intent={
                        countdownSeconds > 0 ? Intent.WARNING : Intent.PRIMARY
                    }
                    icon="refresh"
                    loading={isUpdating}
                    onClick={onUpdateDocument}
                    disabled={
                        isUpdating ||
                        countdownSeconds > 0 ||
                        (cooldownData && !cooldownData.canRefresh)
                    }
                    small
                >
                    {isUpdating
                        ? "Updating..."
                        : countdownSeconds > 0
                        ? `Wait ${countdownSeconds}s`
                        : "Update"}
                </Button>
            </div>
        </div>
    );
}
