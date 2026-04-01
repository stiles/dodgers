/**
 * Manifest loader for consistent dataset access
 * 
 * This module provides a clean interface for loading datasets via the manifest
 * instead of hardcoding URLs throughout the application.
 */

let manifestCache = null;

/**
 * Fetch and cache the manifest
 * @returns {Promise<Object>} The manifest object
 */
export async function getManifest() {
  if (manifestCache) {
    return manifestCache;
  }
  
  // Try local path first (for development), then fallback to S3
  const localUrl = '/data/manifest.json';
  const s3Url = 'https://stilesdata.com/dodgers/data/manifest.json';
  
  try {
    let response = await fetch(localUrl);
    if (!response.ok) {
      // Fallback to S3 URL
      console.log('Local manifest not found, falling back to S3');
      response = await fetch(s3Url);
    }
    
    if (!response.ok) {
      throw new Error(`Failed to fetch manifest: ${response.status}`);
    }
    
    manifestCache = await response.json();
    console.log(`📋 Manifest loaded (v${manifestCache.version}, phase: ${manifestCache.phase}, postseason_active: ${manifestCache.postseason_active})`);
    return manifestCache;
  } catch (error) {
    console.error('❌ Failed to load manifest:', error);
    throw error;
  }
}

/**
 * Get a dataset URL by ID
 * @param {string} datasetId - The dataset identifier
 * @returns {Promise<string>} The dataset URL
 */
export async function getDatasetUrl(datasetId) {
  const manifest = await getManifest();
  const dataset = manifest.datasets.find(d => d.id === datasetId);
  
  if (!dataset) {
    throw new Error(`Dataset not found: ${datasetId}`);
  }
  
  return dataset.url;
}

/**
 * Fetch a dataset by ID
 * @param {string} datasetId - The dataset identifier
 * @returns {Promise<Object>} The parsed JSON dataset
 */
export async function fetchDataset(datasetId) {
  const url = await getDatasetUrl(datasetId);
  
  try {
    const response = await fetch(url);
    if (!response.ok) {
      throw new Error(`Failed to fetch dataset ${datasetId}: ${response.status}`);
    }
    return await response.json();
  } catch (error) {
    console.error(`❌ Failed to load dataset ${datasetId}:`, error);
    throw error;
  }
}

/**
 * Check if postseason section should be visible
 * @returns {Promise<boolean>}
 */
export async function isPostseasonActive() {
  const manifest = await getManifest();
  return manifest.postseason_active === true;
}

/**
 * Get the current season from the manifest
 * @returns {Promise<string>}
 */
export async function getCurrentSeason() {
  const manifest = await getManifest();
  return manifest.season;
}

/**
 * Get the current phase from the manifest
 * @returns {Promise<string>} One of 'regular_season', 'postseason', 'offseason'
 */
export async function getCurrentPhase() {
  const manifest = await getManifest();
  return manifest.phase;
}
