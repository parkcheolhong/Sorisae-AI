export type ZipTextFile = {
    name: string;
    content: string;
};

const CRC32_TABLE = (() => {
    const table = new Uint32Array(256);
    for (let index = 0; index < 256; index += 1) {
        let crc = index;
        for (let bit = 0; bit < 8; bit += 1) {
            crc = (crc & 1) ? (0xedb88320 ^ (crc >>> 1)) : (crc >>> 1);
        }
        table[index] = crc >>> 0;
    }
    return table;
})();

function getDosDateTime(date: Date) {
    const year = Math.max(1980, date.getFullYear());
    const month = date.getMonth() + 1;
    const day = date.getDate();
    const hours = date.getHours();
    const minutes = date.getMinutes();
    const seconds = Math.floor(date.getSeconds() / 2);
    return {
        date: ((year - 1980) << 9) | (month << 5) | day,
        time: (hours << 11) | (minutes << 5) | seconds,
    };
}

function crc32(bytes: Uint8Array) {
    let crc = 0xffffffff;
    for (let index = 0; index < bytes.length; index += 1) {
        crc = CRC32_TABLE[(crc ^ bytes[index]) & 0xff] ^ (crc >>> 8);
    }
    return (crc ^ 0xffffffff) >>> 0;
}

function concatBytes(parts: Uint8Array[]) {
    const totalLength = parts.reduce((sum, part) => sum + part.length, 0);
    const merged = new Uint8Array(totalLength);
    let offset = 0;
    for (const part of parts) {
        merged.set(part, offset);
        offset += part.length;
    }
    return merged;
}

export function buildZipBlob(files: ZipTextFile[]) {
    const encoder = new TextEncoder();
    const now = getDosDateTime(new Date());
    const localParts: Uint8Array[] = [];
    const centralParts: Uint8Array[] = [];
    let offset = 0;

    for (const file of files) {
        const nameBytes = encoder.encode(file.name);
        const contentBytes = encoder.encode(file.content);
        const checksum = crc32(contentBytes);

        const localHeader = new Uint8Array(30 + nameBytes.length);
        const localView = new DataView(localHeader.buffer);
        localView.setUint32(0, 0x04034b50, true);
        localView.setUint16(4, 20, true);
        localView.setUint16(6, 0, true);
        localView.setUint16(8, 0, true);
        localView.setUint16(10, now.time, true);
        localView.setUint16(12, now.date, true);
        localView.setUint32(14, checksum, true);
        localView.setUint32(18, contentBytes.length, true);
        localView.setUint32(22, contentBytes.length, true);
        localView.setUint16(26, nameBytes.length, true);
        localView.setUint16(28, 0, true);
        localHeader.set(nameBytes, 30);

        localParts.push(localHeader, contentBytes);

        const centralHeader = new Uint8Array(46 + nameBytes.length);
        const centralView = new DataView(centralHeader.buffer);
        centralView.setUint32(0, 0x02014b50, true);
        centralView.setUint16(4, 20, true);
        centralView.setUint16(6, 20, true);
        centralView.setUint16(8, 0, true);
        centralView.setUint16(10, 0, true);
        centralView.setUint16(12, now.time, true);
        centralView.setUint16(14, now.date, true);
        centralView.setUint32(16, checksum, true);
        centralView.setUint32(20, contentBytes.length, true);
        centralView.setUint32(24, contentBytes.length, true);
        centralView.setUint16(28, nameBytes.length, true);
        centralView.setUint16(30, 0, true);
        centralView.setUint16(32, 0, true);
        centralView.setUint16(34, 0, true);
        centralView.setUint16(36, 0, true);
        centralView.setUint32(38, 0, true);
        centralView.setUint32(42, offset, true);
        centralHeader.set(nameBytes, 46);
        centralParts.push(centralHeader);

        offset += localHeader.length + contentBytes.length;
    }

    const centralDirectory = concatBytes(centralParts);
    const localDirectory = concatBytes(localParts);
    const eocd = new Uint8Array(22);
    const eocdView = new DataView(eocd.buffer);
    eocdView.setUint32(0, 0x06054b50, true);
    eocdView.setUint16(4, 0, true);
    eocdView.setUint16(6, 0, true);
    eocdView.setUint16(8, files.length, true);
    eocdView.setUint16(10, files.length, true);
    eocdView.setUint32(12, centralDirectory.length, true);
    eocdView.setUint32(16, localDirectory.length, true);
    eocdView.setUint16(20, 0, true);

    return new Blob([localDirectory, centralDirectory, eocd], { type: 'application/zip' });
}

export function downloadZipPackage(fileName: string, files: ZipTextFile[]) {
    if (typeof window === 'undefined') return;
    const blob = buildZipBlob(files);
    const url = window.URL.createObjectURL(blob);
    const anchor = document.createElement('a');
    anchor.href = url;
    anchor.download = fileName;
    document.body.appendChild(anchor);
    anchor.click();
    anchor.remove();
    window.URL.revokeObjectURL(url);
}
