/**
 * ISOLATED TESTING COMPONENT FOR STRUCTURED STORAGE VALIDATION
 * 
 * This component provides a simple UI to test real Onshape structured storage API calls.
 * It's designed to be easily commented out for production.
 * 
 * TODO: Remove this file before production deployment.
 */

import React, { useState } from 'react';
import { Button, Card, Callout, HTMLTable, Pre, Spinner } from '@blueprintjs/core';
import { useSearch } from '@tanstack/react-router';

interface TestResult {
    success: boolean;
    message: string;
    result?: any;
    error?: string;
}

export function StructuredStorageTest() {
    const search = useSearch({ from: "/app/designassistant" });
    const [isLoading, setIsLoading] = useState<string | null>(null);
    const [results, setResults] = useState<Record<string, TestResult>>({});

    // Helper function to make test API calls
    const makeTestCall = async (endpoint: string, method: string = 'GET', description: string) => {
        setIsLoading(description);
        
        try {
            const url = new URL(`/app/test/structured-storage${endpoint}`, window.location.origin);
            
            // Add Onshape document parameters
            const params = new URLSearchParams({
                documentId: search.documentId || '',
                instanceType: search.instanceType || 'w',
                instanceId: search.instanceId || '',
                elementId: search.elementId || '',
                elementType: search.elementType || 'ASSEMBLY'
            });
            
            // Add any additional params from the endpoint
            if (endpoint.includes('?')) {
                const [path, queryString] = endpoint.split('?');
                const additionalParams = new URLSearchParams(queryString);
                additionalParams.forEach((value, key) => {
                    params.set(key, value);
                });
                url.pathname = `/app/test/structured-storage${path}`;
            } else {
                url.pathname = `/app/test/structured-storage${endpoint}`;
            }
            
            url.search = params.toString();
            
            const response = await fetch(url.toString(), {
                method,
                headers: {
                    'Content-Type': 'application/json',
                },
                credentials: 'include'
            });
            
            const data = await response.json();
            
            if (response.ok) {
                setResults(prev => ({
                    ...prev,
                    [description]: {
                        success: true,
                        message: data.message || 'Success',
                        result: data
                    }
                }));
            } else {
                throw new Error(data.message || `HTTP ${response.status}`);
            }
        } catch (error) {
            setResults(prev => ({
                ...prev,
                [description]: {
                    success: false,
                    message: 'Failed',
                    error: error instanceof Error ? error.message : String(error)
                }
            }));
        } finally {
            setIsLoading(null);
        }
    };

    // Test functions
    const testListElements = () => {
        makeTestCall('/test-list-app-elements', 'GET', 'List Application Elements');
    };
    
    const testGetElementId = async () => {
        setIsLoading('Get Element ID');
        
        try {
            const url = new URL('/app/test/structured-storage/test-get-element-id', window.location.origin);
            const params = new URLSearchParams({
                documentId: search.documentId || '',
                instanceType: search.instanceType || 'w',
                instanceId: search.instanceId || '',
                elementId: search.elementId || '',
                elementType: search.elementType || 'ASSEMBLY'
            });
            url.search = params.toString();
            
            const response = await fetch(url.toString(), {
                method: 'GET',
                headers: {
                    'Content-Type': 'application/json',
                },
                credentials: 'include'
            });
            
            const data = await response.json();
            
            if (response.ok && data.element_id) {
                // Copy to clipboard
                await navigator.clipboard.writeText(data.element_id);
                
                setResults(prev => ({
                    ...prev,
                    'Get Element ID': {
                        success: true,
                        message: `Element ID copied to clipboard: ${data.element_id}`,
                        result: data
                    }
                }));
            } else {
                throw new Error(data.message || `HTTP ${response.status}`);
            }
        } catch (error) {
            setResults(prev => ({
                ...prev,
                'Get Element ID': {
                    success: false,
                    message: 'Failed',
                    error: error instanceof Error ? error.message : String(error)
                }
            }));
        } finally {
            setIsLoading(null);
        }
    };
    
    const testCreateElement = () => makeTestCall('/test-create-app-element', 'POST', 'Create Application Element');

    // New individual test functions
    const testUploadData = (appElementId: string) => {
        makeTestCall(`/test-upload-data?appElementId=${appElementId}`, 'POST', 'Upload Test Data');
    };

    const testRetrieveData = (appElementId: string) => {
        makeTestCall(`/test-retrieve-data?appElementId=${appElementId}`, 'GET', 'Retrieve Test Data');
    };

    const testAutomatedBomWorkflow = () => {
        makeTestCall('/test-automated-bom-workflow', 'POST', 'Automated BOM Workflow');
    };

    // Legacy test functions (keep for compatibility)
    const testStoreBomData = (appElementId: string) => {
        makeTestCall(`/test-store-bom-data?appElementId=${appElementId}`, 'POST', 'Store BOM Data');
    };

    const testRetrieveBomData = (appElementId: string) => {
        makeTestCall(`/test-retrieve-bom-data?appElementId=${appElementId}`, 'GET', 'Retrieve BOM Data');
    };

    const testCleanupElement = (appElementId: string) => {
        makeTestCall(`/test-cleanup-app-element?appElementId=${appElementId}`, 'DELETE', 'Cleanup Element');
    };

    // Check if we have valid Onshape parameters
    const hasValidParams = search.documentId && search.elementId && search.instanceId;

    if (!hasValidParams) {
        return (
            <Card>
                <h3>Structured Storage Test</h3>
                <Callout intent="warning">
                    <p>This test requires valid Onshape document parameters.</p>
                    <p>Please open this from within an Onshape Assembly or Part Studio.</p>
                </Callout>
            </Card>
        );
    }

    return (
        <div style={{ padding: '20px', maxWidth: '1200px' }}>
            <Card>
                <h2>🧪 Structured Storage API Test</h2>
                <Callout intent="primary">
                    <strong>TESTING ONLY:</strong> This interface tests real Onshape structured storage API calls.
                    <br />
                    Document: {search.documentId} | Element: {search.elementId} | Type: {search.elementType}
                </Callout>

                <div style={{ marginTop: '20px' }}>
                    <h3>🚀 Automated Workflow</h3>
                    <div style={{ display: 'flex', gap: '10px', flexWrap: 'wrap', marginBottom: '30px', padding: '15px', backgroundColor: '#f8f9fa', borderRadius: '8px', border: '2px solid #28a745' }}>
                        <Button
                            intent="success"
                            large
                            onClick={testAutomatedBomWorkflow}
                            loading={isLoading === 'Automated BOM Workflow'}
                            icon="automatic-updates"
                        >
                            🔄 Run Complete BOM Workflow
                        </Button>
                        <div style={{ marginLeft: '15px', fontSize: '14px', color: '#666' }}>
                            <strong>Complete automation:</strong>
                            <br />• Finds existing FRC elements or creates new one
                            <br />• Loads current BOM data with history tracking
                            <br />• Stores updated analysis with timestamps
                            <br />• Verifies data integrity
                        </div>
                    </div>

                    <h3>Step-by-Step Tests</h3>
                    <div style={{ display: 'flex', gap: '10px', flexWrap: 'wrap', marginBottom: '20px' }}>
                        <Button
                            intent="primary"
                            onClick={testListElements}
                            loading={isLoading === 'List Application Elements'}
                        >
                            1. List All Elements
                        </Button>

                        <Button
                            intent="primary"
                            onClick={testGetElementId}
                            loading={isLoading === 'Get Element ID'}
                        >
                            2. Get Element ID 📋
                        </Button>

                        <Button
                            intent="success"
                            onClick={testCreateElement}
                            loading={isLoading === 'Create Application Element'}
                        >
                            3. Create Test Element
                        </Button>
                    </div>

                    <h3>Upload/Retrieve Tests (Requires Element ID)</h3>
                    <div style={{ display: 'flex', gap: '10px', flexWrap: 'wrap', marginBottom: '20px' }}>
                        <Button
                            intent="warning"
                            onClick={() => {
                                const elementId = prompt('Enter Application Element ID:');
                                if (elementId) testUploadData(elementId);
                            }}
                            loading={isLoading === 'Upload Test Data'}
                        >
                            📤 Upload Test Data
                        </Button>

                        <Button
                            intent="none"
                            onClick={() => {
                                const elementId = prompt('Enter Application Element ID:');
                                if (elementId) testRetrieveData(elementId);
                            }}
                            loading={isLoading === 'Retrieve Test Data'}
                        >
                            📥 Retrieve Test Data
                        </Button>
                    </div>

                    <h3>Legacy Tests (Old Format)</h3>
                    <div style={{ display: 'flex', gap: '10px', flexWrap: 'wrap', marginBottom: '20px' }}>
                        <Button
                            onClick={() => {
                                const elementId = prompt('Enter Application Element ID:');
                                if (elementId) testStoreBomData(elementId);
                            }}
                            loading={isLoading === 'Store BOM Data'}
                        >
                            Store BOM Data (Old)
                        </Button>

                        <Button
                            onClick={() => {
                                const elementId = prompt('Enter Application Element ID:');
                                if (elementId) testRetrieveBomData(elementId);
                            }}
                            loading={isLoading === 'Retrieve BOM Data'}
                        >
                            Retrieve BOM Data (Old)
                        </Button>

                        <Button
                            intent="danger"
                            onClick={() => {
                                const elementId = prompt('Enter Application Element ID to DELETE:');
                                if (elementId && confirm('Are you sure you want to delete this element?')) {
                                    testCleanupElement(elementId);
                                }
                            }}
                            loading={isLoading === 'Cleanup Element'}
                        >
                            🗑️ Delete Element
                        </Button>
                    </div>
                </div>

                {/* Results Display */}
                {Object.keys(results).length > 0 && (
                    <div style={{ marginTop: '30px' }}>
                        <h3>Test Results</h3>
                        <HTMLTable striped style={{ width: '100%' }}>
                            <thead>
                                <tr>
                                    <th>Test</th>
                                    <th>Status</th>
                                    <th>Message</th>
                                    <th>Details</th>
                                </tr>
                            </thead>
                            <tbody>
                                {Object.entries(results).map(([testName, result]) => (
                                    <tr key={testName}>
                                        <td><strong>{testName}</strong></td>
                                        <td>
                                            <span style={{ 
                                                color: result.success ? 'green' : 'red',
                                                fontWeight: 'bold'
                                            }}>
                                                {result.success ? '✅ SUCCESS' : '❌ FAILED'}
                                            </span>
                                        </td>
                                        <td>{result.message}</td>
                                        <td>
                                            {result.error && (
                                                <Callout intent="danger" style={{ marginBottom: '10px' }}>
                                                    <strong>Error:</strong> {result.error}
                                                </Callout>
                                            )}
                                            {result.result && (
                                                <details>
                                                    <summary style={{ cursor: 'pointer', marginBottom: '10px' }}>
                                                        View Full Response
                                                    </summary>
                                                    <Pre style={{ 
                                                        maxHeight: '300px', 
                                                        overflow: 'auto',
                                                        fontSize: '12px',
                                                        backgroundColor: '#f5f5f5',
                                                        padding: '10px',
                                                        color: '#333',
                                                        border: '1px solid #ddd'
                                                    }}>
                                                        {JSON.stringify(result.result, null, 2)}
                                                    </Pre>
                                                </details>
                                            )}
                                        </td>
                                    </tr>
                                ))}
                            </tbody>
                        </HTMLTable>
                    </div>
                )}

                {isLoading && (
                    <div style={{ 
                        position: 'fixed', 
                        top: 0, 
                        left: 0, 
                        right: 0, 
                        bottom: 0, 
                        backgroundColor: 'rgba(0,0,0,0.5)', 
                        display: 'flex', 
                        alignItems: 'center', 
                        justifyContent: 'center',
                        zIndex: 1000
                    }}>
                        <Card style={{ padding: '20px', textAlign: 'center' }}>
                            <Spinner size={50} />
                            <p style={{ marginTop: '15px' }}>
                                <strong>{isLoading}</strong>
                                <br />
                                Making real Onshape API call...
                            </p>
                        </Card>
                    </div>
                )}
            </Card>
        </div>
    );
}