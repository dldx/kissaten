export interface LabelTemplate {
	id: string;
	name: string;
	pageSize: 'A4' | 'A5' | 'Letter';
	width: number; // mm
	height: number; // mm
	rows: number;
	cols: number;
	marginTop: number; // mm
	marginLeft: number; // mm
	marginRight: number; // mm
	marginBottom: number; // mm
	rowGap: number; // mm
	colGap: number; // mm
	labelWidth: number; // mm
	labelHeight: number; // mm
	labelPadding: number; // mm
}

export const PRESET_TEMPLATES: LabelTemplate[] = [
	{
		id: 'avery-5160',
		name: 'Avery 5160 (Letter 3x10)',
		pageSize: 'Letter',
		width: 215.9,
		height: 279.4,
		rows: 10,
		cols: 3,
		marginTop: 12.7,
		marginLeft: 4.8,
		marginRight: 4.8,
		marginBottom: 12.7,
		rowGap: 0,
		colGap: 3.2,
		labelWidth: 66.7,
		labelHeight: 25.4,
		labelPadding: 2
	},
	{
		id: 'a4-3x8',
		name: 'A4 3x8 (24 labels)',
		pageSize: 'A4',
		width: 210,
		height: 297,
		rows: 8,
		cols: 3,
		marginTop: 12.9,
		marginLeft: 7,
		marginRight: 7,
		marginBottom: 12.9,
		rowGap: 0,
		colGap: 2.5,
		labelWidth: 63.5,
		labelHeight: 33.9,
		labelPadding: 2
	},
	{
		id: 'avery-60x60',
		name: 'Avery 60mm x 60mm (Square)',
		pageSize: 'A4',
		width: 210,
		height: 297,
		rows: 4,
		cols: 3,
		marginTop: 23,
		marginLeft: 11,
		marginRight: 11,
		marginBottom: 23,
		rowGap: 4,
		colGap: 4,
		labelWidth: 60,
		labelHeight: 60,
		labelPadding: 4
	}
];
