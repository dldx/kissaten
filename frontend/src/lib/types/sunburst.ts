export interface SunburstData {
	name: string;
	value?: number;
	children?: SunburstData[];
	isOther?: boolean;
}
