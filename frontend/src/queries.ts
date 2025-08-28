import {
    queryOptions,
    useQuery,
    useMutation,
    useQueryClient
} from "@tanstack/react-query";
import { apiGet, apiPost } from "./api/api";
import {
    DocumentObj,
    DocumentsResult,
    ElementsResult,
    Favorite,
    FavoritesResult,
    ElementObj,
    DocumentOrderResult,
} from "./api/backend-types";
import { toUserApiPath, UserPath } from "./api/path";

export function getDocumentsQuery() {
    return queryOptions({
        queryKey: ["documents"],
        queryFn: () =>
            apiGet("/documents").then((result) =>
                Object.fromEntries(
                    result.documents.map((document: DocumentObj) => [
                        document.id,
                        document
                    ])
                )
            ) as Promise<DocumentsResult>
    });
}

export function useDocumentsQuery() {
    return useQuery(getDocumentsQuery());
}

export function getDocumentOrderQuery() {
    return queryOptions({
        queryKey: ["document-order"],
        queryFn: () =>
            apiGet("/document-order").then(
                (result) => result.documentOrder
            ) as Promise<DocumentOrderResult>
    });
}

export function useDocumentOrderQuery() {
    return useQuery(getDocumentOrderQuery());
}

export function getElementsQuery() {
    return queryOptions({
        queryKey: ["elements"],
        queryFn: () =>
            apiGet("/elements").then((result) =>
                Object.fromEntries(
                    result.elements.map((element: ElementObj) => [
                        element.id,
                        element
                    ])
                )
            ) as Promise<ElementsResult>
    });
}

export function useElementsQuery() {
    return useQuery(getElementsQuery());
}

export function getFavoritesQuery(userPath: UserPath) {
    return queryOptions({
        queryKey: ["favorites"],
        queryFn: () =>
            apiGet("/favorites" + toUserApiPath(userPath)).then((result) =>
                Object.fromEntries(
                    result.favorites.map((favorite: Favorite) => [
                        favorite.id,
                        favorite
                    ])
                )
            ) as Promise<FavoritesResult>,
        // Favorites shouldn't go stale, although they can get changed in another tab
        staleTime: 60 * 1000
    });
}

export function useFavoritesQuery(userPath: UserPath) {
    return useQuery(getFavoritesQuery(userPath));
}

// Design Assistant Queries
export function getDesignAssistantDocumentsQuery(onshapeParams?: {
    elementType?: string;
    documentId?: string;
    instanceType?: string;
    instanceId?: string;
    elementId?: string;
}) {
    return queryOptions({
        queryKey: ["design-assistant", "documents", onshapeParams],
        queryFn: () => {
            if (
                !onshapeParams?.documentId ||
                !onshapeParams?.instanceId ||
                !onshapeParams?.elementId
            ) {
                throw new Error("Missing required Onshape parameters");
            }

            // Use query parameters instead of path parameters
            const queryParams: Record<string, string> = {};
            if (onshapeParams.elementType)
                queryParams.elementType = onshapeParams.elementType;
            queryParams.documentId = onshapeParams.documentId;
            queryParams.instanceType = onshapeParams.instanceType || "w";
            queryParams.instanceId = onshapeParams.instanceId;
            queryParams.elementId = onshapeParams.elementId;

            // Build query string
            const queryString = new URLSearchParams(queryParams).toString();
            const url = `/app/designassistant/available-documents?${queryString}`;

            // Use direct fetch since this is not an API endpoint
            return fetch(url).then(async (response) => {
                if (!response.ok) {
                    try {
                        const data = await response.json();
                        if (
                            response.status === 401 &&
                            data?.error === "unauthorized" &&
                            data?.signInUrl
                        ) {
                            window.location.href = data.signInUrl;
                            // Return a promise that never resolves to stop React Query from erroring
                            return new Promise(() => {});
                        }
                    } catch (e) {
                        // ignore json parse error
                    }
                    throw new Error(`HTTP error! status: ${response.status}`);
                }
                return response.json();
            });
        }
    });
}

export function useDesignAssistantDocumentsQuery(onshapeParams?: {
    elementType?: string;
    documentId?: string;
    instanceType?: string;
    instanceId?: string;
    elementId?: string;
}) {
    return useQuery(getDesignAssistantDocumentsQuery(onshapeParams));
}

export function getMissingWeightsQuery() {
    return queryOptions({
        queryKey: ["design-assistant", "missing-weights"],
        queryFn: () =>
            apiGet("/design-assistant/missing-weights").then((result) => result)
    });
}

export function useMissingWeightsQuery() {
    return useQuery(getMissingWeightsQuery());
}

export function getDocumentThumbnailsQuery(documentIds: string[]) {
    return queryOptions({
        queryKey: ["design-assistant", "thumbnails", documentIds],
        queryFn: () =>
            apiGet("/design-assistant/thumbnails", { documentIds }).then(
                (result) => result
            ),
        enabled: documentIds.length > 0
    });
}

export function useDocumentThumbnailsQuery(documentIds: string[]) {
    return useQuery(getDocumentThumbnailsQuery(documentIds));
}

// Design Assistant Mutations
export function useUpdateMaterialMutation() {
    const queryClient = useQueryClient();

    return useMutation({
        mutationFn: ({
            documentId,
            material,
            density
        }: {
            documentId: string;
            material: string;
            density?: number;
        }) =>
            apiPost("/design-assistant/update-material", {
                body: { documentId, material, density }
            }),
        onSuccess: () => {
            // Invalidate and refetch design assistant data
            queryClient.invalidateQueries({ queryKey: ["design-assistant"] });
        }
    });
}

// BOM Analysis Queries
export function getBomIngestQuery() {
    return queryOptions({
        queryKey: ["design-assistant", "bom-ingest"],
        queryFn: (bomData: any) =>
            apiPost("/design-assistant/ingest", {
                body: bomData
            })
    });
}

export function useBomIngestMutation() {
    const queryClient = useQueryClient();

    return useMutation({
        mutationFn: (bomData: any) =>
            apiPost("/design-assistant/ingest", {
                body: bomData
            }),
        onSuccess: () => {
            // Invalidate and refetch BOM-related data
            queryClient.invalidateQueries({
                queryKey: ["design-assistant", "bom"]
            });
        }
    });
}

export function getWeightMetricsQuery(enabled: boolean = true) {
    return queryOptions({
        queryKey: ["design-assistant", "weight-metrics"],
        queryFn: async () => {
            const response = await fetch("/app/designassistant/metrics/weight");
            if (!response.ok) {
                throw new Error(
                    `Failed to fetch weight metrics: ${response.status}`
                );
            }
            return response.json();
        },
        enabled
    });
}

export function useWeightMetricsQuery(enabled: boolean = true) {
    return useQuery(getWeightMetricsQuery(enabled));
}

export function getMissingMaterialReportQuery(enabled: boolean = true) {
    return queryOptions({
        queryKey: ["design-assistant", "missing-material-report"],
        queryFn: async () => {
            const response = await fetch(
                "/app/designassistant/reports/missing-material"
            );
            if (!response.ok) {
                throw new Error(
                    `Failed to fetch missing material report: ${response.status}`
                );
            }
            return response.json();
        },
        enabled
    });
}

export function useMissingMaterialReportQuery(enabled: boolean = true) {
    return useQuery(getMissingMaterialReportQuery(enabled));
}

// BOM Data Query
export function getBomDataQuery(onshapeParams?: {
    elementType?: string;
    documentId?: string;
    instanceType?: string;
    instanceId?: string;
    elementId?: string;
    forceRefresh?: boolean;
}) {
    return queryOptions({
        queryKey: ["design-assistant", "bom-data", onshapeParams],
        queryFn: async () => {
            if (
                !onshapeParams?.documentId ||
                !onshapeParams?.instanceId ||
                !onshapeParams?.elementId
            ) {
                throw new Error("Missing required Onshape parameters");
            }

            const queryParams: Record<string, string> = {};
            if (onshapeParams.elementType)
                queryParams.elementType = onshapeParams.elementType;
            queryParams.documentId = onshapeParams.documentId;
            queryParams.instanceType = onshapeParams.instanceType || "w";
            queryParams.instanceId = onshapeParams.instanceId;
            queryParams.elementId = onshapeParams.elementId;

            // Add force refresh parameter if specified
            if (onshapeParams.forceRefresh) {
                queryParams.forceRefresh = "true";
            }

            const queryString = new URLSearchParams(queryParams).toString();
            const url = `/app/designassistant/bom?${queryString}`;

            const response = await fetch(url);
            if (!response.ok) {
                throw new Error(`Failed to fetch BOM data: ${response.status}`);
            }
            return response.json();
        }
    });
}

export function useBomDataQuery(onshapeParams?: {
    elementType?: string;
    documentId?: string;
    instanceType?: string;
    instanceId?: string;
    elementId?: string;
    forceRefresh?: boolean;
}) {
    return useQuery(getBomDataQuery(onshapeParams));
}

export function getRefreshCooldownQuery(onshapeParams?: {
    elementType?: string;
    documentId?: string;
    instanceType?: string;
    instanceId?: string;
    elementId?: string;
}) {
    return queryOptions({
        queryKey: ["design-assistant", "refresh-cooldown", onshapeParams],
        queryFn: async () => {
            if (!onshapeParams?.documentId || !onshapeParams?.elementId) {
                throw new Error("documentId and elementId are required");
            }

            const queryParams: Record<string, string> = {};
            if (onshapeParams.elementType)
                queryParams.elementType = onshapeParams.elementType;
            if (onshapeParams.documentId)
                queryParams.documentId = onshapeParams.documentId;
            if (onshapeParams.instanceType)
                queryParams.instanceType = onshapeParams.instanceType;
            if (onshapeParams.instanceId)
                queryParams.instanceId = onshapeParams.instanceId;
            if (onshapeParams.elementId)
                queryParams.elementId = onshapeParams.elementId;

            const queryString = new URLSearchParams(queryParams).toString();
            const url = `/app/designassistant/refresh-cooldown?${queryString}`;

            const response = await fetch(url);
            if (!response.ok) {
                throw new Error(
                    `Failed to fetch refresh cooldown: ${response.status}`
                );
            }
            return response.json();
        },
        refetchInterval: 1000 // Check every second for countdown
    });
}

export function useRefreshCooldownQuery(onshapeParams?: {
    elementType?: string;
    documentId?: string;
    instanceType?: string;
    instanceId?: string;
    elementId?: string;
}) {
    return useQuery(getRefreshCooldownQuery(onshapeParams));
}

