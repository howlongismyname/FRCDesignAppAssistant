import { queryClient } from "../query-client";
import { Outlet, useSearch } from "@tanstack/react-router";
import { QueryClientProvider } from "@tanstack/react-query";
import { getBackgroundClass, getThemeClass } from "../api/onshape-params";
import { BlueprintProvider } from "@blueprintjs/core";
import { SettingsMenu } from "../navbar/settings-menu";
import { InsertMenu } from "../document/insert-menu";
import { TanStackRouterDevtools } from "@tanstack/react-router-devtools";
import { AddDocumentMenu } from "../document/add-document-menu";

export function DesignAssistant() {
    const search = useSearch({ from: "/app/designassistant" });

    const themeClass = getThemeClass(search.theme);
    return (
        <BlueprintProvider
            portalClassName={themeClass}
            portalContainer={document.getElementById("root")!}
        >
            <QueryClientProvider client={queryClient}>
                <div className={themeClass + " app-background"}>
                    <div
                        className={
                            getBackgroundClass(search.theme) + " app-content"
                        }
                    >
                        <Outlet />
                        <SettingsMenu />
                        <InsertMenu />
                        <AddDocumentMenu />
                        <TanStackRouterDevtools />
                    </div>
                </div>
            </QueryClientProvider>
        </BlueprintProvider>
    );
}
