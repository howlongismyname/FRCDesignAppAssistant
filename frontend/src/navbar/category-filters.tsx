import { Button, ButtonVariant, Intent, Tag } from "@blueprintjs/core";
import { useLocation, useNavigate, useSearch } from "@tanstack/react-router";
import { ReactNode } from "react";
import { CotsCategory } from "../api/backend-types";

export function CategoryFilters(): ReactNode {
    const navigate = useNavigate();
    const pathname = useLocation().pathname;
    const cotsCategories = useSearch({ from: "/app" }).cotsCategories;

    const areAllTagsActive = cotsCategories === undefined;

    const filterTags = Object.values(CotsCategory).map((category) => {
        const isCategoryActive = areAllTagsActive || cotsCategories.includes(category);
        return (
            <Tag
                round
                interactive
                key={category}
                intent={Intent.SUCCESS}
                title={category}
                onClick={() => {
                    let newCategories;
                    if (areAllTagsActive) {
                        newCategories = [category];
                    } else if (isCategoryActive) {
                        newCategories = cotsCategories.filter((curr) => curr !== category);
                        if (newCategories.length === 0) {
                            newCategories = undefined;
                        }
                    } else {
                        newCategories = [...cotsCategories, category];
                    }
                    navigate({ to: pathname, search: { cotsCategories: newCategories } });
                }}
                active={!isCategoryActive} // The active prop of tags is backwards
            >
                {category}
            </Tag>
        );
    });

    const clearButton = (
        <Button
            text="Clear"
            disabled={areAllTagsActive}
            variant={ButtonVariant.OUTLINED}
            icon="small-cross"
            onClick={() => {
                navigate({ to: pathname, search: { cotsCategories: undefined } });
            }}
        />
    );

    return (
        <div className="center" style={{ gap: "5px" }}>
            <div className="category-filter-tags">{filterTags}</div>
            {clearButton}
        </div>
    );
}