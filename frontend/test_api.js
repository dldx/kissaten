// Simple test script to verify the API client works with clean URLs
import { api } from './src/lib/api.ts';

async function testCleanUrls() {
    try {
        console.log('Testing search endpoint with clean URLs...');

        // Test search to get some beans with clean URLs
        const searchResponse = await api.search({ limit: 3 });
        if (searchResponse.success && searchResponse.data) {
            console.log('Search successful!');

            const firstBean = searchResponse.data[0];
            console.log('First bean:', {
                name: firstBean.name,
                roaster: firstBean.roaster,
                clean_url_slug: firstBean.clean_url_slug,
                bean_url_path: firstBean.bean_url_path
            });

            // Test URL parsing
            if (firstBean.bean_url_path) {
                const parsed = api.parseBeanUrl(firstBean.bean_url_path);
                console.log('Parsed URL:', parsed);

                if (parsed) {
                    // Test clean URL access
                    console.log('Testing clean URL access...');
                    const beanResponse = await api.getBeanByCleanUrl(parsed.roasterSlug, parsed.beanSlug);
                    if (beanResponse.success) {
                        console.log('Clean URL access successful!');
                        console.log('Retrieved bean:', beanResponse.data?.name);
                    } else {
                        console.error('Clean URL access failed');
                    }
                }
            }
        } else {
            console.error('Search failed:', searchResponse);
        }

    } catch (error) {
        console.error('Test failed:', error);
    }
}

testCleanUrls();
