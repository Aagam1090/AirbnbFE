import { Component } from '@angular/core';
import { FormBuilder, FormGroup, Validators,FormArray } from '@angular/forms';
import { HttpClient, HttpParams } from '@angular/common/http';
import { GetcityService } from '../service/getcity.service';

@Component({
  selector: 'app-search',
  templateUrl: './search.component.html',
  styleUrls: ['./search.component.css']
})
export class SearchComponent {
  registrationForm: FormGroup;
  cityList: string[] = [];
  amenitiesList: string[] = ['Pool', 'Gym', 'Parking', 'WiFi','Kitchen','Washer'];
  apiUrl = 'http://127.0.0.1:5000/search';
  displayForm = true;
  displayResults = false;
  dataresponse: any;

  ngOnInit() {
    this.getCityService.getCities().subscribe(cities => {
      console.log('Cities:', cities);
      this.cityList = cities;
    });
  }

  constructor(private formBuilder: FormBuilder,private http: HttpClient,private getCityService: GetcityService) {
    this.registrationForm = this.formBuilder.group({
      name: [''],
      city: ['', Validators.required],
      priceMin: ['', [Validators.required, Validators.min(0)]],
      priceMax: ['', [Validators.required, Validators.min(0)]],
      bedrooms: ['', [Validators.min(1), Validators.max(30)]],
      people: ['', [Validators.min(1), Validators.max(30)]],
      amenities: [this.getDefaultAmenities()],
      rating: ['', [Validators.min(1), Validators.max(10)]],
      neighborhood: ['']
    }, { validators: this.priceRangeValidator });
  }

  priceRangeValidator(form: FormGroup): { [key: string]: any } | null {
    const min = form.get('priceMin')?.value || 0;
    const max = form.get('priceMax')?.value || 0;
    return min !== null && max !== null && min <= max ? null : { 'priceRangeInvalid': true };
  }
  getDefaultAmenities(): string[] {
    // Return an empty array if no default value is desired
    // or return an array with default selected values
    return []; // This sets the amenities to have no pre-selected values
  }

  submitForm() {
    if (this.registrationForm.valid) {
      const params = new HttpParams({ fromObject: this.registrationForm.value });
      this.http.get(this.apiUrl, { params }).subscribe(
        response => {
          console.log('Search results:', response);
          this.dataresponse = response;
          this.displayForm = false;
          this.displayResults = true;
        },
        error => {
          console.error('Error:', error);
        }
      );
    } else {
      console.error('Form is not valid');
    }
  }

  handleBack(): void {
    this.displayResults = false;
    this.displayForm = true; // Show the search form again
  }

}
