export const DESIGN_IMAGE_POOL = [
    '/design/pdf-set/image_03d68b00-5ab1-4b95-bb8a-3da206dcf342.png',
    '/design/pdf-set/image_1c1cbd34-42c0-4935-b297-27241cfdf72b.png',
    '/design/pdf-set/image_2f385721-8050-4016-b855-af10cb73f131.png',
    '/design/pdf-set/image_318d8256-af43-40a9-bec9-6edba5652437.png',
    '/design/pdf-set/image_34090eed-0c2b-4789-a44f-ad718f2049eb.png',
    '/design/pdf-set/image_36fb8121-346b-4c82-8827-71b3b6d6b568.png',
    '/design/pdf-set/image_3e084d57-ad1f-4a3b-a98c-14f77306b093.png',
    '/design/pdf-set/image_3fe84f39-6ab7-4855-9767-4e3dd1819b6d.png',
    '/design/pdf-set/image_47d63c48-d5c7-46d3-b4b9-76950b6d3b55.png',
    '/design/pdf-set/image_4a091aef-01f1-418e-8998-a650fb336816.png',
    '/design/pdf-set/image_4c903aec-19fe-4c62-b989-a42fd9656e29.png',
    '/design/pdf-set/image_51ef3e8e-6f88-48ea-a02c-ef3300111c0c.png',
    '/design/pdf-set/image_646d0911-5a94-4f66-84f6-ccb587477470.png',
    '/design/pdf-set/image_665c6ee1-c409-4caa-8c40-705549f9868e.png',
    '/design/pdf-set/image_6c93ec91-60f1-47aa-9ebd-f271372da5c6.png',
    '/design/pdf-set/image_745878dc-b199-4046-a8bc-f1351be79a67.png',
    '/design/pdf-set/image_770ae4c0-ba8b-4e26-9d89-5b8dd26dad92.png',
    '/design/pdf-set/image_8cff711b-b369-47c4-a52a-3936af360390.png',
    '/design/pdf-set/image_94663eb1-6cde-4004-a4d2-2c4e9b8fd247.png',
    '/design/pdf-set/image_95daa1c2-c443-4ecf-b4de-f4b226fd5cf4.png',
    '/design/pdf-set/image_a75bcdfb-3fcb-42c0-9b81-abccaa93d36d.png',
    '/design/pdf-set/image_aa95f36e-b9ea-4823-b6d1-ba2898aba922.png',
    '/design/pdf-set/image_ab7b7e0d-90da-47ac-8b2b-84862dfa0caf.png',
    '/design/pdf-set/image_b01b9711-0c3c-4174-a47a-03010590e1d3.png',
    '/design/pdf-set/image_ba7483e0-b640-48a1-ab7e-75d27d7db81f.png',
    '/design/pdf-set/image_d1d5efba-2554-4b04-868b-d4a5a4f3e27c.png',
    '/design/pdf-set/image_d69fbfb2-486e-43b8-bdbb-8de81dcd9c52.png',
    '/design/pdf-set/image_d7a53337-8e58-409a-9e35-f2c15eb7c0a5.png',
    '/design/pdf-set/image_ddbbcb70-2a12-4497-a690-a32e71ea45da.png',
    '/design/pdf-set/image_fc26a41a-d6b0-4df3-a8b5-74ffaa5e9d37.png',
    '/design/pdf-set/image_fc94a59f-04b2-4ad2-ac3e-9a5857d21ceb.png',
    '/design/pdf-set/image_fd49d027-de1c-4553-a035-a2423cf092fe.png',
    '/design/pdf-set/image_fe3ded75-2767-42f6-9add-b11108b99c5c.png',
];

export const DESIGN_PAGE_HERO = {
    marketplace: DESIGN_IMAGE_POOL[0],
    web: DESIGN_IMAGE_POOL[2],
    detail: DESIGN_IMAGE_POOL[6],
    upload: DESIGN_IMAGE_POOL[11],
    edit: DESIGN_IMAGE_POOL[16],
    dashboard: DESIGN_IMAGE_POOL[20],
    mobile: DESIGN_IMAGE_POOL[24],
    handbook: DESIGN_IMAGE_POOL[28],
    adminDashboard: DESIGN_IMAGE_POOL[31],
} as const;

export const DESIGN_ACTION_THUMBNAILS = [DESIGN_IMAGE_POOL[1], DESIGN_IMAGE_POOL[2], DESIGN_IMAGE_POOL[3]];
export const DESIGN_PREVIEW_GRID = [DESIGN_IMAGE_POOL[7], DESIGN_IMAGE_POOL[12], DESIGN_IMAGE_POOL[18]];
export const DESIGN_MOBILE_GRID = [
    DESIGN_IMAGE_POOL[4],
    DESIGN_IMAGE_POOL[5],
    DESIGN_IMAGE_POOL[8],
    DESIGN_IMAGE_POOL[9],
    DESIGN_IMAGE_POOL[10],
    DESIGN_IMAGE_POOL[13],
];

export const DESIGN_WEB_GRID = [
    DESIGN_IMAGE_POOL[14],
    DESIGN_IMAGE_POOL[15],
    DESIGN_IMAGE_POOL[17],
    DESIGN_IMAGE_POOL[19],
    DESIGN_IMAGE_POOL[21],
    DESIGN_IMAGE_POOL[22],
];

export const DESIGN_HANDBOOK_GRID = [
    DESIGN_IMAGE_POOL[23],
    DESIGN_IMAGE_POOL[25],
    DESIGN_IMAGE_POOL[26],
    DESIGN_IMAGE_POOL[27],
    DESIGN_IMAGE_POOL[29],
    DESIGN_IMAGE_POOL[30],
    DESIGN_IMAGE_POOL[31],
    DESIGN_IMAGE_POOL[32],
];

export const DESIGN_ADMIN_GRID = [
    DESIGN_IMAGE_POOL[0],
    DESIGN_IMAGE_POOL[3],
    DESIGN_IMAGE_POOL[6],
    DESIGN_IMAGE_POOL[11],
    DESIGN_IMAGE_POOL[16],
    DESIGN_IMAGE_POOL[20],
];

export function getDesignImageByIndex(index: number) {
    return DESIGN_IMAGE_POOL[Math.abs(index) % DESIGN_IMAGE_POOL.length];
}
